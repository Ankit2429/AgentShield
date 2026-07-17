"""Analyze router for AgentShield API v1.

Endpoint
--------
``POST /api/v1/analyze``

Orchestrates the full security pipeline for one AI agent request:

1. Create a :class:`~app.core.events.schema.SecurityEvent`.
2. Run :class:`~app.core.detector.DetectionEngine`.
3. Register a Behavioral DNA observation and run deviation analysis.
4. Register / update the agent's trust profile.
5. Run :class:`~app.core.decision_engine.DecisionEngine`.
6. Build a replay session and return it alongside the full analysis result.

Design constraint
-----------------
This router contains **only orchestration logic**.  No security decisions,
scoring arithmetic, or rule matching live here — all of that is delegated
to the existing engines via dependency injection.

Future extension points
-----------------------
TODO [AUTH]:       Validate a JWT bearer token and extract the caller identity
                   before running the pipeline.
TODO [RATE_LIMIT]: Apply per-agent rate limiting before creating the event.
TODO [STREAM]:     Add ``POST /analyze/stream`` that yields SSE frames as each
                   engine stage completes.
TODO [ASYNC]:      Convert the pipeline to ``async`` and run Detection + DNA
                   concurrently with ``asyncio.gather``.
TODO [WEBHOOK]:    Dispatch a webhook to caller-registered URLs when the
                   decision is ``BLOCK`` or ``QUARANTINE``.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from app.core.ws import ws_manager
from app.config import settings

from app.api.deps import (
    get_decision_engine,
    get_detection_engine,
    get_dna_engine,
    get_replay_engine,
    get_timeline_builder,
    get_trust_engine,
    require_roles,
)
from app.core.replay_protector import replay_protector
from app.core.auth_matrix import auth_matrix
from app.core.interceptor import message_interceptor
from app.api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    BehaviorSummary,
    DecisionSummary,
    DetectionSummary,
    ThreatItem,
    TrustSummary,
)
from app.core.behavior_dna import BehaviorDNAEngine, BehaviorObservation
from app.core.decision_engine import DecisionEngine
from app.core.detector import DetectionEngine
from app.core.events import enrich, make_event, obs_from_event
from app.core.replay import ReplayEngine, TimelineBuilder
from app.core.trust_engine import TrustEngine

router = APIRouter(prefix="/analyze", tags=["Analyze"])


# ============================================================================
# POST /analyze
# ============================================================================


@router.post(
    "",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles("Admin", "Security Analyst"))],
    summary="Analyze an AI Agent Message",
    description=(
        "Runs a message through the full AgentShield security pipeline: "
        "Detection → Behavioral DNA → Trust → Decision. "
        "Returns a structured result and creates a replay session."
    ),
)
async def analyze(
    request: AnalyzeRequest,
    detection_engine: DetectionEngine = Depends(get_detection_engine),
    trust_engine: TrustEngine = Depends(get_trust_engine),
    decision_engine: DecisionEngine = Depends(get_decision_engine),
    dna_engine: BehaviorDNAEngine = Depends(get_dna_engine),
    replay_engine: ReplayEngine = Depends(get_replay_engine),
    timeline_builder: TimelineBuilder = Depends(get_timeline_builder),
) -> AnalyzeResponse:
    """Process one AI agent message through the full security pipeline.

    Args:
        request: Validated :class:`~app.api.schemas.AnalyzeRequest` body.
        detection_engine: Injected :class:`~app.core.detector.DetectionEngine`.
        trust_engine: Injected :class:`~app.core.trust_engine.TrustEngine`.
        decision_engine: Injected :class:`~app.core.decision_engine.DecisionEngine`.
        dna_engine: Injected :class:`~app.core.behavior_dna.BehaviorDNAEngine`.
        replay_engine: Injected :class:`~app.core.replay.ReplayEngine`.
        timeline_builder: Injected :class:`~app.core.replay.TimelineBuilder`.

    Returns:
        :class:`~app.api.schemas.AnalyzeResponse` with all engine outputs and
        the replay session ID.

    Raises:
        :exc:`fastapi.HTTPException` 500: If the pipeline raises an unexpected
        exception.  The replay session is failed before re-raising.
    """
    # ── Replay Protection Deduplication ─────────────────────────────────────
    client_event_id = request.metadata.get("event_id") or request.metadata.get("event_uuid")
    import uuid
    event_id = str(client_event_id) if client_event_id else str(uuid.uuid4())

    if not replay_protector.check_and_register(
        event_id=event_id,
        agent_id=request.agent_id,
        message=request.message,
        tool=request.requested_tool
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate request payload or event ID detected. Request rejected by replay protection engine."
        )

    # ── 1. Create SecurityEvent ───────────────────────────────────────────────
    event = make_event(
        agent_id=request.agent_id,
        message=request.message,
        requested_tool=request.requested_tool,
        metadata=request.metadata,
        event_id=event_id,
    )

    # Open a replay session immediately so we can fail it gracefully.
    session = replay_engine.create_session(event.event_id, event.agent_id)

    # Broadcast Stage 1: RECEIVED
    await ws_manager.broadcast({
        "type": "pipeline_progress",
        "stage": "RECEIVED",
        "agent_id": event.agent_id,
        "session_id": session.session_id,
        "data": {
            "message": event.message,
            "requested_tool": event.requested_tool,
            "timestamp": event.timestamp.isoformat()
        }
    })

    try:
        # Claimed role can be provided in metadata (defaults to 'viewer_agent')
        claimed_role = request.metadata.get("agent_role") or "viewer_agent"
        identity_spoofed = not auth_matrix.verify_agent_identity(event.agent_id, claimed_role)

        # Capability Matrix Check (prevents Tool Abuse & Unauthorized Tool Calls)
        auth_matrix_authorized = True
        if event.requested_tool:
            resource = request.metadata.get("resource") or "default_resource"
            auth_matrix_authorized = auth_matrix.check_authorization(claimed_role, event.requested_tool, resource)

        # Interceptor checks (Indirect Prompt Injection, Loops, Cross-Agent, Exfil)
        interceptor_res = message_interceptor.intercept_message(
            message=event.message,
            session_id=session.session_id,
            agent_id=event.agent_id,
            requested_tool=event.requested_tool,
            context=request.metadata,
        )
        interceptor_findings = interceptor_res.get("findings", [])

        # ── 2. Detection ──────────────────────────────────────────────────────
        if settings.DEMO_MODE:
            await asyncio.sleep(0.3)
        det_result = detection_engine.analyze(event.message)
        event = enrich(event, detection_result=det_result)

        # Broadcast Stage 2: DETECTION
        await ws_manager.broadcast({
            "type": "pipeline_progress",
            "stage": "DETECTION",
            "agent_id": event.agent_id,
            "session_id": session.session_id,
            "data": {
                "is_malicious": det_result.is_malicious,
                "risk_score": det_result.risk_score,
                "threat_count": det_result.threat_count
            }
        })

        # ── 3. Behavioral DNA ─────────────────────────────────────────────────
        if settings.DEMO_MODE:
            await asyncio.sleep(0.3)
        obs = obs_from_event(event)
        dna_engine.register_observation(event.agent_id, obs)
        ba = dna_engine.analyze_behavior(event.agent_id, obs)
        event = enrich(event, behavior_analysis=ba)

        # Broadcast Stage 3: BEHAVIOR
        await ws_manager.broadcast({
            "type": "pipeline_progress",
            "stage": "BEHAVIOR",
            "agent_id": event.agent_id,
            "session_id": session.session_id,
            "data": {
                "behavior_similarity": ba.behavior_similarity if ba else 1.0,
                "behavior_deviation": ba.behavior_deviation if ba else 0.0,
                "deviation_level": ba.deviation_level.value if ba else "NORMAL",
                "summary": ba.summary if ba else "Insufficent baseline"
            }
        })

        # ── 4. Trust ──────────────────────────────────────────────────────────
        if settings.DEMO_MODE:
            await asyncio.sleep(0.3)
        # Register agent pre-decision so that behavior/policy can be computed
        trust_profile = trust_engine.register_agent(event.agent_id)
        event = enrich(event, trust_profile=trust_profile)

        # Broadcast Stage 4: TRUST (Preliminary trust snapshot with pre-decision state)
        await ws_manager.broadcast({
            "type": "pipeline_progress",
            "stage": "TRUST",
            "agent_id": event.agent_id,
            "session_id": session.session_id,
            "data": {
                "trust_score": trust_profile.trust_score,
                "behavior_score": trust_profile.behavior_score,
                "policy_score": trust_profile.policy_score,
                "security_grade": trust_profile.security_grade,
                "status": trust_profile.status.value,
                "trend": trust_profile.trend.value
            }
        })

        # ── 5. Decision ───────────────────────────────────────────────────────
        if settings.DEMO_MODE:
            await asyncio.sleep(0.3)
        eval_context = {
            "identity_spoofed": identity_spoofed,
            "auth_matrix_authorized": auth_matrix_authorized,
            "interceptor_findings": interceptor_findings,
        }
        # Pass pre-decision trust profile into decide()
        decision_result = decision_engine.decide(
            detection_result=det_result,
            trust_profile=trust_profile,
            requested_tool=event.requested_tool,
            context=eval_context,
        )
        event = enrich(event, decision_result=decision_result)

        # Broadcast Stage 5: DECISION
        await ws_manager.broadcast({
            "type": "pipeline_progress",
            "stage": "DECISION",
            "agent_id": event.agent_id,
            "session_id": session.session_id,
            "data": {
                "decision": decision_result.decision.value,
                "confidence": decision_result.confidence,
                "severity": decision_result.severity.value,
                "explanation": decision_result.explanation
            }
        })

        # Record trust outcome after decision based on decision outcome
        if decision_result.decision.value in ("BLOCK", "QUARANTINE"):
            final_trust_profile = trust_engine.record_block(event.agent_id)
        else:
            final_trust_profile = trust_engine.record_success(event.agent_id)
        event = enrich(event, trust_profile=final_trust_profile)

        # Broadcast Stage 4: TRUST (Corrected/final trust update after decision)
        await ws_manager.broadcast({
            "type": "pipeline_progress",
            "stage": "TRUST",
            "agent_id": event.agent_id,
            "session_id": session.session_id,
            "data": {
                "trust_score": final_trust_profile.trust_score,
                "behavior_score": final_trust_profile.behavior_score,
                "policy_score": final_trust_profile.policy_score,
                "security_grade": final_trust_profile.security_grade,
                "status": final_trust_profile.status.value,
                "trend": final_trust_profile.trend.value
            }
        })

        # ── 6. Build and complete replay session ──────────────────────────────
        if settings.DEMO_MODE:
            await asyncio.sleep(0.3)
        for frame in timeline_builder.build(event):
            replay_engine.add_frame(session.session_id, frame)
        summary = TimelineBuilder.generate_summary(event)
        replay_engine.complete_session(session.session_id, summary)
        message_interceptor.clear_session(session.session_id)

        # Broadcast Stage 6: REPLAY
        await ws_manager.broadcast({
            "type": "pipeline_progress",
            "stage": "REPLAY",
            "agent_id": event.agent_id,
            "session_id": session.session_id,
            "data": {
                "session_id": session.session_id
            }
        })

    except Exception as exc:  # noqa: BLE001
        replay_engine.fail_session(session.session_id, str(exc))
        message_interceptor.clear_session(session.session_id)
        detail_msg = "Internal pipeline evaluation error. Audit session aborted."
        if settings.APP_ENV == "development":
            detail_msg = f"Pipeline error: {exc}"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail_msg,
        ) from exc

    # ── 7. Translate engine outputs → Pydantic response ──────────────────────
    response = _build_analyze_response(event, session.session_id)
    response_dict = jsonable_encoder(response)

    # Broadcast final NEW_ANALYSIS payload
    await ws_manager.broadcast({
        "type": "NEW_ANALYSIS",
        "data": response_dict
    })

    # Broadcast TRUST_UPDATE
    await ws_manager.broadcast({
        "type": "TRUST_UPDATE",
        "agent_id": event.agent_id,
        "trust": response_dict["trust"]
    })

    return response


# ============================================================================
# Private translation helpers
# ============================================================================


def _build_analyze_response(event, session_id: str) -> AnalyzeResponse:
    """Translate a fully enriched SecurityEvent into :class:`~app.api.schemas.AnalyzeResponse`.

    Args:
        event: Enriched :class:`~app.core.events.schema.SecurityEvent`.
        session_id: ID of the completed replay session.

    Returns:
        :class:`~app.api.schemas.AnalyzeResponse`.
    """
    det = event.detection_result
    ba = event.behavior_analysis
    tp = event.trust_profile
    dr = event.decision_result

    detection = DetectionSummary(
        is_malicious=det.is_malicious,
        risk_score=det.risk_score,
        threat_count=det.threat_count,
        threats=[
            ThreatItem(
                name=t.rule.name,
                category=t.rule.category,
                severity=t.rule.severity.name,
                matched_text=t.matched_text,
            )
            for t in det.threats[:10]
        ],
    )

    behavior: BehaviorSummary | None = None
    if ba is not None:
        behavior = BehaviorSummary(
            behavior_similarity=ba.behavior_similarity,
            behavior_deviation=ba.behavior_deviation,
            deviation_level=ba.deviation_level.value,
            reasons=list(ba.reasons[:10]),
            summary=ba.summary,
        )

    trust = TrustSummary(
        trust_score=tp.trust_score,
        behavior_score=tp.behavior_score,
        policy_score=tp.policy_score,
        security_grade=tp.security_grade,
        status=tp.status.value,
        trend=tp.trend.value,
    )

    reason_codes = [
        r.value if hasattr(r, "value") else str(r)
        for r in getattr(dr, "reasoning", [])
    ]
    decision_val = dr.decision
    severity_val = dr.severity
    rec_val = dr.recommendation

    decision = DecisionSummary(
        decision=decision_val.value if hasattr(decision_val, "value") else str(decision_val),
        confidence=dr.confidence,
        severity=severity_val.value if hasattr(severity_val, "value") else str(severity_val),
        recommendation=rec_val.value if hasattr(rec_val, "value") else str(rec_val),
        reason_codes=reason_codes,
        explanation=dr.explanation,
        risk_score=dr.risk_score or 0.0,
    )

    return AnalyzeResponse(
        event_id=event.event_id,
        agent_id=event.agent_id,
        session_id=session_id,
        timestamp=event.timestamp,
        stage=event.enrichment_stage,
        detection=detection,
        behavior=behavior,
        trust=trust,
        decision=decision,
    )
