"""SecurityEvent lifecycle definitions and utilities for AgentShield X.

This module defines the canonical enrichment lifecycle of a
:class:`~app.core.events.schema.SecurityEvent` and provides helpers that
consume a fully enriched event to answer operational questions.

Lifecycle stages
----------------
Each stage name corresponds to the value returned by
:attr:`~app.core.events.schema.SecurityEvent.enrichment_stage`:

``raw``
    The event was just created by :func:`~app.core.events.schema.make_event`.
    No engine has processed it yet.

``detected``
    :class:`~app.core.detector.DetectionEngine` has run; ``detection_result``
    is present.

``behavior_analyzed``
    :class:`~app.core.behavior_dna.BehaviorDNAEngine` has run;
    ``behavior_analysis`` is present.  (May occur before or after
    ``trust_profile`` is set.)

``profiled``
    :class:`~app.core.trust_engine.TrustEngine` has run; ``trust_profile``
    is present.

``complete``
    :class:`~app.core.decision_engine.DecisionEngine` has run;
    ``decision_result`` is present.  The event has passed through all core
    security engines.

Extension points
----------------
TODO [REPLAY]:   Implement ``EventReplayEngine`` that reads a stream of
                 serialised events and replays them through the pipeline.
TODO [AUDIT]:    Implement ``AuditEmitter`` that writes a structured audit
                 log entry for every completed event.
TODO [SCHEMA_V]: Add event schema versioning (``schema_version`` field) so
                 that deserialisers can handle events from older deployments.
TODO [TTL]:      Add a TTL / expiry mechanism for in-memory event stores so
                 stale raw events are automatically evicted.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from app.core.events.schema import SecurityEvent


# ============================================================================
# Lifecycle stage enumeration
# ============================================================================


class EventStage(str, Enum):
    """Canonical enrichment stage labels for a :class:`SecurityEvent`.

    These values exactly match those returned by
    :attr:`~app.core.events.schema.SecurityEvent.enrichment_stage` so they
    can be used for comparison without string literals scattered in calling
    code.

    Attributes:
        RAW: No engine has processed the event yet.
        DETECTED: Detection result is present.
        BEHAVIOR_ANALYZED: Behavioral DNA analysis is present.
        PROFILED: Trust profile is present.
        COMPLETE: Decision result is present; all core engines have run.
    """

    RAW = "raw"
    DETECTED = "detected"
    BEHAVIOR_ANALYZED = "behavior_analyzed"
    PROFILED = "profiled"
    COMPLETE = "complete"


# ============================================================================
# Lifecycle query helpers
# ============================================================================


def event_stage(event: SecurityEvent) -> EventStage:
    """Return the current :class:`EventStage` of *event*.

    Args:
        event: The event to inspect.

    Returns:
        :class:`EventStage` corresponding to the current enrichment state.

    Example::

        stage = event_stage(event)
        if stage == EventStage.COMPLETE:
            emit_to_audit_log(event)
    """
    raw_stage = event.enrichment_stage
    try:
        return EventStage(raw_stage)
    except ValueError:
        return EventStage.RAW


def assert_stage_at_least(event: SecurityEvent, required: EventStage) -> None:
    """Raise :exc:`RuntimeError` if *event* has not yet reached *required* stage.

    Useful as a guard at the start of engine functions that depend on upstream
    enrichment.

    Args:
        event: The event to check.
        required: The minimum :class:`EventStage` that must be reached.

    Raises:
        RuntimeError: If the event's current stage is earlier than *required*.

    Example::

        # Guard inside a function that needs detection results
        assert_stage_at_least(event, EventStage.DETECTED)
        risk = event.detection_result.risk_score
    """
    _stage_order: dict[EventStage, int] = {
        EventStage.RAW: 0,
        EventStage.DETECTED: 1,
        EventStage.BEHAVIOR_ANALYZED: 2,
        EventStage.PROFILED: 3,
        EventStage.COMPLETE: 4,
    }
    current = event_stage(event)
    if _stage_order.get(current, 0) < _stage_order.get(required, 0):
        raise RuntimeError(
            f"Event {event.event_id!r} is at stage {current.value!r} "
            f"but {required.value!r} is required."
        )


def is_actionable(event: SecurityEvent) -> bool:
    """Return ``True`` when *event* carries enough information to act on.

    An event is actionable when both ``detection_result`` and ``trust_profile``
    are present — the minimum required for a Decision Engine call.

    Args:
        event: The event to inspect.

    Returns:
        bool: ``True`` when at least detection and trust data are available.
    """
    return (
        event.detection_result is not None
        and event.trust_profile is not None
    )


def event_risk_score(event: SecurityEvent) -> float:
    """Extract the risk score from *event*, or ``0.0`` if not yet detected.

    Args:
        event: The event to query.

    Returns:
        float: Risk score in ``[0.0, 1.0]``, or ``0.0`` if no detection result
        is present.
    """
    if event.detection_result is None:
        return 0.0
    return float(getattr(event.detection_result, "risk_score", 0.0))


def event_decision_value(event: SecurityEvent) -> str:
    """Extract the decision string from *event*, or ``"PENDING"`` if not decided.

    Args:
        event: The event to query.

    Returns:
        str: Decision value (e.g. ``"BLOCK"``) or ``"PENDING"`` when the
        Decision Engine has not yet run.
    """
    if event.decision_result is None:
        return "PENDING"
    decision = getattr(event.decision_result, "decision", None)
    if decision is None:
        return "UNKNOWN"
    return decision.value if hasattr(decision, "value") else str(decision)


def to_audit_dict(event: SecurityEvent) -> dict[str, Any]:
    """Serialise *event* into a flat dict suitable for an audit log.

    All engine result objects are reduced to their key numeric / string
    fields so the audit record has no dependency on engine-specific types.

    Args:
        event: The event to serialise (may be at any stage).

    Returns:
        dict[str, Any]: Flat, JSON-serialisable audit record.

    Note:
        TODO [AUDIT]: Route this dict to the AuditLogger instead of returning
        it; the caller should not need to do the routing manually.

        TODO [SCHEMA_V]: Embed a ``schema_version`` key so downstream
        consumers can handle format changes gracefully.
    """
    record: dict[str, Any] = {
        "event_id": event.event_id,
        "timestamp": event.timestamp.isoformat(),
        "agent_id": event.agent_id,
        "requested_tool": event.requested_tool,
        "message_length": len(event.message),
        "stage": event.enrichment_stage,
        "metadata": event.metadata,
    }

    if event.detection_result is not None:
        det = event.detection_result
        record["detection"] = {
            "is_malicious": getattr(det, "is_malicious", None),
            "risk_score": getattr(det, "risk_score", None),
            "threat_count": getattr(det, "threat_count", None),
            "categories": list({
                t.rule.category
                for t in getattr(det, "threats", [])
            }),
        }

    if event.behavior_analysis is not None:
        ba = event.behavior_analysis
        level = getattr(ba, "deviation_level", None)
        record["behavior"] = {
            "similarity": getattr(ba, "behavior_similarity", None),
            "deviation": getattr(ba, "behavior_deviation", None),
            "level": level.value if hasattr(level, "value") else str(level),
            "reason_count": len(getattr(ba, "reasons", [])),
        }

    if event.trust_profile is not None:
        tp = event.trust_profile
        status = getattr(tp, "status", None)
        trend = getattr(tp, "trend", None)
        record["trust"] = {
            "trust_score": getattr(tp, "trust_score", None),
            "behavior_score": getattr(tp, "behavior_score", None),
            "policy_score": getattr(tp, "policy_score", None),
            "security_grade": getattr(tp, "security_grade", None),
            "status": status.value if hasattr(status, "value") else str(status),
            "trend": trend.value if hasattr(trend, "value") else str(trend),
        }

    if event.authorization_result is not None:
        record["authorization"] = event.authorization_result

    if event.decision_result is not None:
        dr = event.decision_result
        decision = getattr(dr, "decision", None)
        severity = getattr(dr, "severity", None)
        recommendation = getattr(dr, "recommendation", None)
        reasons = getattr(dr, "reasoning", [])
        record["decision"] = {
            "decision_id": getattr(dr, "decision_id", None),
            "decision": decision.value if hasattr(decision, "value") else str(decision),
            "confidence": getattr(dr, "confidence", None),
            "severity": severity.value if hasattr(severity, "value") else str(severity),
            "recommendation": (
                recommendation.value
                if hasattr(recommendation, "value")
                else str(recommendation)
            ),
            "reason_codes": [
                r.value if hasattr(r, "value") else str(r) for r in reasons
            ],
            "explanation": getattr(dr, "explanation", None),
        }

    return record
