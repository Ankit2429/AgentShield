"""Timeline Builder for the AgentShield Attack Replay Engine.

This module is the bridge between a fully (or partially) enriched
:class:`~app.core.events.schema.SecurityEvent` and an ordered sequence of
:class:`~app.core.replay.replay_models.ReplayFrame` objects.

The :class:`TimelineBuilder` inspects each enrichment field of the event and
produces a corresponding :class:`~app.core.replay.replay_models.ReplayFrame`
that captures the key numeric signals, human-readable titles, and
engine-specific metadata for that stage.

Design philosophy
-----------------
* **Stage isolation** — each private ``_build_*_frame`` method is responsible
  for exactly one stage and never reads another stage's data.  This makes it
  safe to add, remove, or reorder stages without touching other methods.
* **Graceful degradation** — if an enrichment field is ``None``, its stage is
  silently skipped.  Partial timelines (e.g. a pipeline that failed after
  detection) are fully supported.
* **Lossy-safe** — the builder extracts only primitive types (floats, strings,
  ints, lists of strings) into :attr:`~app.core.replay.replay_models.ReplayFrame.metadata`
  so the resulting frames can always be serialised to JSON without further
  processing.

Stage to frame mapping
----------------------

.. code-block:: text

    SecurityEvent field        ReplayStage
    ─────────────────────────  ─────────────────────
    (always)                   RECEIVED
    detection_result           DETECTED
    behavior_analysis          BEHAVIOR_ANALYZED
    trust_profile              TRUST_UPDATED
    decision_result            DECISION_MADE
    (always, at build time)    AUDITED  ← terminal frame

Full build example::

    from app.core.replay.timeline import TimelineBuilder
    from app.core.replay.replay_engine import ReplayEngine

    builder = TimelineBuilder()
    engine  = ReplayEngine()

    session = engine.create_session(event.event_id, event.agent_id)

    for frame in builder.build(event):
        engine.add_frame(session.session_id, frame)

    summary = builder.generate_summary(event)
    engine.complete_session(session.session_id, summary)

Future extension points
-----------------------
TODO [MITRE]:      Annotate ``DETECTED`` frames with MITRE ATT&CK technique
                   IDs derived from the detected threat categories.
TODO [DIFF]:       Compare consecutive frames of the same stage across two
                   events to generate a diff-style timeline for attack chains.
TODO [CUSTOM_STAGES]: Support caller-registered custom stages so plugin engines
                   can inject their own frames without modifying this module.
TODO [COMPRESSION]: Collapse consecutive NORMAL/ALLOW frames into a single
                   summary frame when building long multi-event timelines.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterator, Optional

from app.core.replay.replay_models import (
    ReplayFrame,
    ReplayStage,
    make_frame,
)

# Import SecurityEvent only for type hints — avoid circular imports at runtime.
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.events.schema import SecurityEvent


# ============================================================================
# Stage metadata constants (titles & engine labels)
# ============================================================================

_STAGE_META: dict[ReplayStage, dict[str, str]] = {
    ReplayStage.RECEIVED: {
        "title": "Event Received",
        "engine": "system",
    },
    ReplayStage.DETECTED: {
        "title": "Threat Detection",
        "engine": "DetectionEngine",
    },
    ReplayStage.BEHAVIOR_ANALYZED: {
        "title": "Behavioral Analysis",
        "engine": "BehaviorDNAEngine",
    },
    ReplayStage.TRUST_UPDATED: {
        "title": "Trust Evaluation",
        "engine": "TrustEngine",
    },
    ReplayStage.DECISION_MADE: {
        "title": "Security Decision",
        "engine": "DecisionEngine",
    },
    ReplayStage.AUDITED: {
        "title": "Audit Record",
        "engine": "AuditLogger",
    },
}


# ============================================================================
# TimelineBuilder
# ============================================================================


class TimelineBuilder:
    """Convert a :class:`~app.core.events.schema.SecurityEvent` into an ordered
    sequence of :class:`~app.core.replay.replay_models.ReplayFrame` objects.

    The builder is **stateless** — a single instance can safely be shared
    across threads and called concurrently without any locking.

    Typical usage::

        builder = TimelineBuilder()

        # Iterate frames as they are produced
        for frame in builder.build(event):
            replay_engine.add_frame(session_id, frame)

        # Or collect all frames at once
        frames = builder.build_all(event)
    """

    # =========================================================================
    # Public API
    # =========================================================================

    def build(self, event: Any) -> Iterator[ReplayFrame]:
        """Yield :class:`~app.core.replay.replay_models.ReplayFrame` objects
        in canonical pipeline order for the given *event*.

        Stages whose corresponding enrichment field is ``None`` are silently
        skipped.  The ``RECEIVED`` and ``AUDITED`` frames are always produced.

        Args:
            event: A :class:`~app.core.events.schema.SecurityEvent` (typed as
                ``Any`` to avoid a runtime circular import).

        Yields:
            :class:`~app.core.replay.replay_models.ReplayFrame` in pipeline
            order.

        Example::

            for frame in builder.build(event):
                print(frame.stage, frame.title)
        """
        yield self._build_received_frame(event)

        if getattr(event, "detection_result", None) is not None:
            yield self._build_detection_frame(event)

        if getattr(event, "behavior_analysis", None) is not None:
            yield self._build_behavior_frame(event)

        if getattr(event, "trust_profile", None) is not None:
            yield self._build_trust_frame(event)

        if getattr(event, "decision_result", None) is not None:
            yield self._build_decision_frame(event)

        yield self._build_audit_frame(event)

    def build_all(self, event: Any) -> list[ReplayFrame]:
        """Return all frames as a list (eager version of :meth:`build`).

        Args:
            event: A :class:`~app.core.events.schema.SecurityEvent`.

        Returns:
            list[ReplayFrame]: All frames in canonical pipeline order.
        """
        return list(self.build(event))

    @staticmethod
    def generate_summary(event: Any) -> str:
        """Produce a one-sentence overall summary for a completed replay session.

        Reads the highest-priority available enrichment field and composes a
        human-readable verdict sentence.

        Args:
            event: A :class:`~app.core.events.schema.SecurityEvent`.

        Returns:
            str: Human-readable summary (never empty).

        Example::

            summary = TimelineBuilder.generate_summary(event)
            # "Agent blocked: command injection detected (risk 0.92), "
            # "trust score 0.23, decision BLOCK with confidence 0.87."
        """
        parts: list[str] = []

        # Decision fragment
        dr = getattr(event, "decision_result", None)
        if dr is not None:
            decision = getattr(dr, "decision", None)
            decision_str = decision.value if hasattr(decision, "value") else str(decision)
            confidence = getattr(dr, "confidence", None)
            conf_str = f" (confidence {confidence:.0%})" if confidence is not None else ""
            parts.append(f"Decision: {decision_str}{conf_str}")

        # Detection fragment
        det = getattr(event, "detection_result", None)
        if det is not None:
            risk = getattr(det, "risk_score", None)
            count = getattr(det, "threat_count", None)
            if risk is not None:
                threat_str = (
                    f"{count} threat{'s' if (count or 0) != 1 else ''} detected, "
                    if count
                    else ""
                )
                parts.append(f"{threat_str}risk score {risk:.2f}")

        # Trust fragment
        tp = getattr(event, "trust_profile", None)
        if tp is not None:
            trust = getattr(tp, "trust_score", None)
            grade = getattr(tp, "security_grade", None)
            if trust is not None:
                grade_str = f" (grade {grade})" if grade else ""
                parts.append(f"trust score {trust:.2f}{grade_str}")

        # Behavior fragment
        ba = getattr(event, "behavior_analysis", None)
        if ba is not None:
            level = getattr(ba, "deviation_level", None)
            if level is not None:
                level_str = level.value if hasattr(level, "value") else str(level)
                parts.append(f"behavioral deviation {level_str}")

        if not parts:
            return "Event processed with no enrichment data available."

        return "; ".join(parts) + "."

    # =========================================================================
    # Private frame builders — one per stage
    # =========================================================================

    @staticmethod
    def _build_received_frame(event: Any) -> ReplayFrame:
        """Build the ``RECEIVED`` frame for *event*.

        This frame always exists and captures the raw event metadata.

        Args:
            event: Source :class:`~app.core.events.schema.SecurityEvent`.

        Returns:
            :class:`~app.core.replay.replay_models.ReplayFrame`.
        """
        meta = _STAGE_META[ReplayStage.RECEIVED]
        msg = getattr(event, "message", "")
        tool = getattr(event, "requested_tool", None)
        agent_id = getattr(event, "agent_id", "unknown")
        event_meta = getattr(event, "metadata", {})

        tool_str = f" requesting tool '{tool}'" if tool else ""
        description = (
            f"Agent '{agent_id}' submitted a {len(msg)}-character message{tool_str}."
        )

        return make_frame(
            stage=ReplayStage.RECEIVED,
            title=meta["title"],
            description=description,
            engine=meta["engine"],
            timestamp=getattr(event, "timestamp", None) or datetime.now(timezone.utc),
            metadata={
                "agent_id": agent_id,
                "message_length": len(msg),
                "requested_tool": tool,
                "event_id": getattr(event, "event_id", ""),
                "context": dict(event_meta),
            },
        )

    @staticmethod
    def _build_detection_frame(event: Any) -> ReplayFrame:
        """Build the ``DETECTED`` frame from ``event.detection_result``.

        Args:
            event: Source event with ``detection_result`` populated.

        Returns:
            :class:`~app.core.replay.replay_models.ReplayFrame`.
        """
        meta = _STAGE_META[ReplayStage.DETECTED]
        det = event.detection_result

        risk = getattr(det, "risk_score", 0.0)
        count = getattr(det, "threat_count", 0)
        is_malicious = getattr(det, "is_malicious", False)
        threats = getattr(det, "threats", [])

        categories = list({
            getattr(getattr(t, "rule", None), "category", "unknown")
            for t in threats
        })
        threat_names = [
            getattr(getattr(t, "rule", None), "name", "unknown")
            for t in threats[:5]
        ]

        if is_malicious:
            cat_str = ", ".join(categories) if categories else "unknown"
            description = (
                f"{count} threat pattern{'s' if count != 1 else ''} detected "
                f"(categories: {cat_str}). Risk score: {risk:.2f}."
            )
        else:
            description = f"No threat patterns detected. Risk score: {risk:.2f}."

        # TODO [MITRE]: Append MITRE ATT&CK technique IDs to metadata here.
        return make_frame(
            stage=ReplayStage.DETECTED,
            title=meta["title"],
            description=description,
            engine=meta["engine"],
            risk_score=risk,
            metadata={
                "is_malicious": is_malicious,
                "threat_count": count,
                "risk_score": risk,
                "categories": categories,
                "threat_names": threat_names,
            },
        )

    @staticmethod
    def _build_behavior_frame(event: Any) -> ReplayFrame:
        """Build the ``BEHAVIOR_ANALYZED`` frame from ``event.behavior_analysis``.

        Args:
            event: Source event with ``behavior_analysis`` populated.

        Returns:
            :class:`~app.core.replay.replay_models.ReplayFrame`.
        """
        meta = _STAGE_META[ReplayStage.BEHAVIOR_ANALYZED]
        ba = event.behavior_analysis

        similarity = getattr(ba, "behavior_similarity", None)
        deviation = getattr(ba, "behavior_deviation", None)
        level = getattr(ba, "deviation_level", None)
        reasons = getattr(ba, "reasons", [])
        summary = getattr(ba, "summary", "")

        level_str = level.value if hasattr(level, "value") else str(level)
        sim_str = f"{similarity:.0%}" if similarity is not None else "N/A"
        dev_str = f"{deviation:.0%}" if deviation is not None else "N/A"

        description = (
            f"Behavioral similarity to baseline: {sim_str} "
            f"(deviation {dev_str}). Level: {level_str}."
        )
        if reasons:
            description += f" {len(reasons)} anomaly signal{'s' if len(reasons) != 1 else ''} flagged."

        return make_frame(
            stage=ReplayStage.BEHAVIOR_ANALYZED,
            title=meta["title"],
            description=description,
            engine=meta["engine"],
            metadata={
                "behavior_similarity": similarity,
                "behavior_deviation": deviation,
                "deviation_level": level_str,
                "reason_count": len(reasons),
                "reasons": list(reasons[:10]),  # cap to avoid huge payloads
                "summary": summary,
            },
        )

    @staticmethod
    def _build_trust_frame(event: Any) -> ReplayFrame:
        """Build the ``TRUST_UPDATED`` frame from ``event.trust_profile``.

        Args:
            event: Source event with ``trust_profile`` populated.

        Returns:
            :class:`~app.core.replay.replay_models.ReplayFrame`.
        """
        meta = _STAGE_META[ReplayStage.TRUST_UPDATED]
        tp = event.trust_profile

        trust = getattr(tp, "trust_score", None)
        behavior_score = getattr(tp, "behavior_score", None)
        policy_score = getattr(tp, "policy_score", None)
        grade = getattr(tp, "security_grade", None)
        status = getattr(tp, "status", None)
        trend = getattr(tp, "trend", None)
        obs = getattr(tp, "observations", None)

        status_str = status.value if hasattr(status, "value") else str(status)
        trend_str = trend.value if hasattr(trend, "value") else str(trend)
        trust_str = f"{trust:.2f}" if trust is not None else "N/A"

        description = (
            f"Agent trust score: {trust_str} (grade {grade}). "
            f"Status: {status_str}. Trend: {trend_str}."
        )

        return make_frame(
            stage=ReplayStage.TRUST_UPDATED,
            title=meta["title"],
            description=description,
            engine=meta["engine"],
            trust_score=trust,
            metadata={
                "trust_score": trust,
                "behavior_score": behavior_score,
                "policy_score": policy_score,
                "security_grade": grade,
                "status": status_str,
                "trend": trend_str,
                "total_observations": obs,
                "successful_requests": getattr(tp, "successful_requests", None),
                "blocked_requests": getattr(tp, "blocked_requests", None),
                "suspicious_requests": getattr(tp, "suspicious_requests", None),
            },
        )

    @staticmethod
    def _build_decision_frame(event: Any) -> ReplayFrame:
        """Build the ``DECISION_MADE`` frame from ``event.decision_result``.

        Args:
            event: Source event with ``decision_result`` populated.

        Returns:
            :class:`~app.core.replay.replay_models.ReplayFrame`.
        """
        meta = _STAGE_META[ReplayStage.DECISION_MADE]
        dr = event.decision_result
        tp = getattr(event, "trust_profile", None)

        decision = getattr(dr, "decision", None)
        decision_str = decision.value if hasattr(decision, "value") else str(decision)
        confidence = getattr(dr, "confidence", None)
        severity = getattr(dr, "severity", None)
        recommendation = getattr(dr, "recommendation", None)
        reasoning = getattr(dr, "reasoning", [])
        explanation = getattr(dr, "explanation", "")
        risk_score = getattr(dr, "risk_score", None)
        trust_score = getattr(dr, "trust_score", None) or (
            getattr(tp, "trust_score", None) if tp else None
        )

        severity_str = severity.value if hasattr(severity, "value") else str(severity)
        rec_str = recommendation.value if hasattr(recommendation, "value") else str(recommendation)
        conf_str = f" (confidence {confidence:.0%})" if confidence is not None else ""
        reason_codes = [
            r.value if hasattr(r, "value") else str(r) for r in reasoning
        ]

        description = (
            f"Decision: {decision_str}{conf_str}. "
            f"Recommendation: {rec_str}. "
            f"Severity: {severity_str}."
        )

        return make_frame(
            stage=ReplayStage.DECISION_MADE,
            title=meta["title"],
            description=description,
            engine=meta["engine"],
            risk_score=risk_score,
            trust_score=trust_score,
            decision=decision_str,
            metadata={
                "decision": decision_str,
                "confidence": confidence,
                "severity": severity_str,
                "recommendation": rec_str,
                "reason_codes": reason_codes,
                "explanation": explanation,
                "decision_id": getattr(dr, "decision_id", None),
            },
        )

    @staticmethod
    def _build_audit_frame(event: Any) -> ReplayFrame:
        """Build the terminal ``AUDITED`` frame for *event*.

        This frame always exists and marks the end of the replay timeline.
        It captures the final enrichment stage and a compact event summary.

        Args:
            event: Source :class:`~app.core.events.schema.SecurityEvent`.

        Returns:
            :class:`~app.core.replay.replay_models.ReplayFrame`.

        Note:
            TODO [AUDIT]: Integrate with the AuditLogger to emit a structured
            log entry at this point rather than producing a synthetic frame.
        """
        meta = _STAGE_META[ReplayStage.AUDITED]
        stage = getattr(event, "enrichment_stage", "unknown")
        is_complete = getattr(event, "is_complete", False)

        description = (
            f"Event audit record written. "
            f"Final stage: {stage}. "
            f"Pipeline complete: {is_complete}."
        )

        # Capture the compact summary dict for auditability.
        try:
            event_summary = event.summary()
        except Exception:
            event_summary = {}

        return make_frame(
            stage=ReplayStage.AUDITED,
            title=meta["title"],
            description=description,
            engine=meta["engine"],
            metadata={
                "final_stage": stage,
                "is_complete": is_complete,
                "event_summary": event_summary,
            },
        )
