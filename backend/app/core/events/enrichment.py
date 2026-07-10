"""SecurityEvent enrichment helpers for AgentShield X.

This module provides the single function that all engine callers use to attach
their output to an existing :class:`~app.core.events.schema.SecurityEvent`.

Design constraint
-----------------
Each engine produces its result independently and **never calls another
engine**.  Instead, the caller (typically a request pipeline in ``main.py``
or a future ``SecurityPipeline`` orchestrator) enriches the event step by
step::

    event = make_event(agent_id, message, tool)

    # Step 1 – Detection
    det_result = detection_engine.analyze(event.message)
    event = enrich(event, detection_result=det_result)

    # Step 2 – Behavior DNA
    dna_engine.register_observation(event.agent_id, obs_from_event(event))
    analysis = dna_engine.analyze_behavior(event.agent_id, obs_from_event(event))
    event = enrich(event, behavior_analysis=analysis)

    # Step 3 – Trust
    trust_profile = trust_engine.register_agent(event.agent_id)
    event = enrich(event, trust_profile=trust_profile)

    # Step 4 – Decision
    decision = decision_engine.decide(
        detection_result=event.detection_result,
        trust_profile=event.trust_profile,
        requested_tool=event.requested_tool,
    )
    event = enrich(event, decision_result=decision)

    assert event.is_complete

Immutability guarantee
----------------------
Every call to :func:`enrich` returns a **new** ``SecurityEvent`` via
``dataclasses.replace``; the original object is never modified.  This makes
events safe to share across threads and simple to replay.

Extension points
----------------
TODO [REPLAY]:   Store each enriched snapshot to a durable log before
                 returning so the full event history can be reconstructed.
TODO [VALIDATE]: Add per-field validators to reject incompatible enrichment
                 types at the boundary (e.g. ensure detection_result is a
                 real DetectionResult, not an arbitrary dict).
TODO [HOOKS]:    Support a list of pre-/post-enrichment hooks that plugins
                 can register (e.g. streaming to a SIEM, triggering alerts).
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Optional

from app.core.events.schema import SecurityEvent


def enrich(
    event: SecurityEvent,
    *,
    detection_result: Optional[Any] = None,
    behavior_analysis: Optional[Any] = None,
    trust_profile: Optional[Any] = None,
    authorization_result: Optional[dict[str, Any]] = None,
    decision_result: Optional[Any] = None,
) -> SecurityEvent:
    """Return a new :class:`~app.core.events.schema.SecurityEvent` enriched
    with the supplied engine output(s).

    Only fields explicitly passed as keyword arguments are updated.  Fields
    not mentioned retain their current values (including existing enrichments).
    Passing ``None`` for a field has no effect — it does **not** clear an
    existing enrichment.

    Args:
        event: The source event to enrich (never mutated).
        detection_result: Output of
            :class:`~app.core.detector.DetectionEngine`.
        behavior_analysis: Output of
            :class:`~app.core.behavior_dna.BehaviorDNAEngine`.
        trust_profile: The agent's
            :class:`~app.core.trust_engine.AgentTrustProfile` snapshot.
        authorization_result: Raw dict from the AuthMatrix engine (future).
        decision_result: Output of
            :class:`~app.core.decision_engine.DecisionEngine`.

    Returns:
        A **new** :class:`~app.core.events.schema.SecurityEvent` with the
        specified enrichments applied.  The original event is unchanged.

    Example::

        event = make_event("agent-1", "hello")
        det   = detection_engine.analyze(event.message)
        event = enrich(event, detection_result=det)
        assert event.detection_result is det
        assert event.is_enriched

    Note:
        TODO [REPLAY]: Snapshot the enriched event to a durable log here
        before returning so every intermediate state is recoverable.

        TODO [HOOKS]: Invoke registered enrichment hooks here (e.g. forward
        to a SIEM or trigger a streaming alert).
    """
    # Build a dict of only the fields that the caller actually supplied.
    updates: dict[str, Any] = {}

    if detection_result is not None:
        updates["detection_result"] = detection_result
    if behavior_analysis is not None:
        updates["behavior_analysis"] = behavior_analysis
    if trust_profile is not None:
        updates["trust_profile"] = trust_profile
    if authorization_result is not None:
        updates["authorization_result"] = authorization_result
    if decision_result is not None:
        updates["decision_result"] = decision_result

    if not updates:
        # Nothing to update — return the original event unchanged.
        return event

    # TODO [VALIDATE]: Enforce type contracts for each enrichment field here
    #                  before calling dataclasses.replace.

    return replace(event, **updates)


def obs_from_event(event: SecurityEvent) -> Any:
    """Construct a :class:`~app.core.behavior_dna.BehaviorObservation` from
    an enriched event.

    This is a convenience factory that bridges the enrichment pipeline with
    the Behavioral DNA Engine.  It requires ``detection_result`` to be present
    on *event* to extract the risk score and threat categories.

    Args:
        event: A :class:`~app.core.events.schema.SecurityEvent` with at least
            ``detection_result`` set.

    Returns:
        A :class:`~app.core.behavior_dna.BehaviorObservation` ready to be
        passed to
        :meth:`~app.core.behavior_dna.BehaviorDNAEngine.register_observation`
        or :meth:`~app.core.behavior_dna.BehaviorDNAEngine.analyze_behavior`.

    Raises:
        ValueError: If ``detection_result`` has not yet been set on *event*.

    Example::

        event = enrich(event, detection_result=det_result)
        obs   = obs_from_event(event)
        dna_engine.register_observation(event.agent_id, obs)

    Note:
        TODO [FINGERPRINT]: Attach the agent's current ``fingerprint_id``
        from the BehaviorProfile to the observation so the DNA engine can
        detect sudden identity shifts.
    """
    if event.detection_result is None:
        raise ValueError(
            "obs_from_event() requires event.detection_result to be set. "
            "Enrich the event with detection results first."
        )

    # Import here (not at module level) to avoid circular imports.
    from app.core.behavior_dna import BehaviorObservation  # noqa: PLC0415

    det = event.detection_result
    threat_categories: list[str] = list(
        {t.rule.category for t in getattr(det, "threats", [])}
    )

    return BehaviorObservation(
        requested_tool=event.requested_tool,
        message_length=len(event.message),
        risk_score=getattr(det, "risk_score", 0.0),
        threat_categories=threat_categories,
        timestamp=event.timestamp,
    )
