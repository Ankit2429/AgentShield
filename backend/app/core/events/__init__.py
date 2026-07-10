"""AgentShield X — Security Event Bus package.

This sub-package defines the shared communication contract between all
security engines: a single, immutable :class:`~app.core.events.schema.SecurityEvent`
that is progressively enriched as a request flows through the detection,
behavioral, trust, and decision pipeline.

Sub-modules
-----------
:mod:`app.core.events.schema`
    The :class:`~app.core.events.schema.SecurityEvent` dataclass and the
    :func:`~app.core.events.schema.make_event` factory.

:mod:`app.core.events.enrichment`
    The :func:`~app.core.events.enrichment.enrich` function (returns enriched
    event copies) and the :func:`~app.core.events.enrichment.obs_from_event`
    bridge to the Behavioral DNA Engine.

:mod:`app.core.events.lifecycle`
    :class:`~app.core.events.lifecycle.EventStage` enum, lifecycle query
    helpers, and the :func:`~app.core.events.lifecycle.to_audit_dict`
    serialiser.

Quickstart::

    from app.core.events import (
        SecurityEvent,
        make_event,
        enrich,
        obs_from_event,
        EventStage,
        event_stage,
        to_audit_dict,
    )

    event = make_event(
        agent_id="agent-1",
        message="list /etc/passwd",
        requested_tool="file_read",
    )
    # ... run engines, call enrich() at each step ...
    print(event.is_complete)
    print(to_audit_dict(event))
"""

from app.core.events.enrichment import enrich, obs_from_event
from app.core.events.lifecycle import (
    EventStage,
    assert_stage_at_least,
    event_decision_value,
    event_risk_score,
    event_stage,
    is_actionable,
    to_audit_dict,
)
from app.core.events.schema import SecurityEvent, make_event

__all__ = [
    # ── Schema ───────────────────────────────────────────────────────────────
    "SecurityEvent",
    "make_event",
    # ── Enrichment ────────────────────────────────────────────────────────────
    "enrich",
    "obs_from_event",
    # ── Lifecycle ─────────────────────────────────────────────────────────────
    "EventStage",
    "event_stage",
    "assert_stage_at_least",
    "is_actionable",
    "event_risk_score",
    "event_decision_value",
    "to_audit_dict",
]
