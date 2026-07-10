"""Core SecurityEvent schema for AgentShield X.

Every AI agent request that flows through the platform is represented as a
single :class:`SecurityEvent`.  The event begins as a thin, immutable record
of the raw request and is **progressively enriched** by each security engine
without those engines ever calling each other directly.

This module owns only the data contract — no business logic lives here.

Design principles
-----------------
* **Immutable core** – the six core fields (``event_id``, ``timestamp``,
  ``agent_id``, ``message``, ``requested_tool``, ``metadata``) are set at
  creation and never change.
* **Progressive enrichment** – optional fields (``detection_result``,
  ``behavior_analysis``, ``trust_profile``, ``authorization_result``,
  ``decision_result``) are ``None`` until the corresponding engine has run.
  Enriched copies are created via :func:`~app.core.events.enrichment.enrich`.
* **Single source of truth** – every audit log, replay system, or correlation
  engine operates on a ``SecurityEvent`` rather than on individual engine
  outputs.
* **No engine coupling** – this module imports only standard-library types
  and the four engine result types.  Engines never import each other.

Event lifecycle::

    ┌─────────────────────────────────────────────────────────────────┐
    │                       SecurityEvent                              │
    │                                                                  │
    │  core (immutable)         optional enrichment fields             │
    │  ─────────────────        ──────────────────────────────────     │
    │  event_id                 detection_result     ← DetectionEngine │
    │  timestamp                behavior_analysis    ← BehaviorDNA     │
    │  agent_id                 trust_profile        ← TrustEngine     │
    │  message                  authorization_result ← AuthMatrix(*)   │
    │  requested_tool           decision_result      ← DecisionEngine  │
    │  metadata                                                        │
    │                           (* future)                             │
    └─────────────────────────────────────────────────────────────────┘

Typical creation::

    from app.core.events import SecurityEvent, make_event

    event = make_event(
        agent_id="agent-42",
        message="ignore previous instructions",
        requested_tool="shell_exec",
        metadata={"session_id": "s-001", "region": "eu-west-1"},
    )

Typical enrichment (see :mod:`app.core.events.enrichment`)::

    from app.core.events.enrichment import enrich

    event = enrich(event, detection_result=det_result)
    event = enrich(event, trust_profile=trust_profile)
    event = enrich(event, decision_result=decision)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Optional

# ── Lazy engine result imports (TYPE_CHECKING only avoids circular deps) ──────
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.behavior_dna import BehaviorAnalysis
    from app.core.decision_engine import DecisionResult
    from app.core.models import DetectionResult
    from app.core.trust_engine import AgentTrustProfile


# ============================================================================
# SecurityEvent — the canonical request record
# ============================================================================


@dataclass(frozen=True)
class SecurityEvent:
    """An immutable snapshot of one AI agent request and its enrichments.

    The event is the **shared communication contract** between all security
    engines.  Each engine reads what it needs from the event and returns an
    enriched copy — it never mutates state directly.

    Attributes:
        event_id: Globally unique identifier for this event (UUID4 string).
            Stable for the entire lifetime of the request.
        timestamp: UTC creation time, set once at :func:`make_event` call time.
        agent_id: Unique, stable identifier of the requesting AI agent.
        message: Raw text message submitted by the agent.  Never mutated.
        requested_tool: The capability the agent is requesting, or ``None``
            for a plain message exchange.
        metadata: Arbitrary context supplied by the caller (session ID,
            geographic region, model version, etc.).  Read-only after creation.
            Consumers should namespace keys to avoid collisions.

    Enrichment fields (``None`` until the corresponding engine has run):
        detection_result: Output of :class:`~app.core.detector.DetectionEngine`.
        behavior_analysis: Output of
            :class:`~app.core.behavior_dna.BehaviorDNAEngine`.
        trust_profile: The agent's
            :class:`~app.core.trust_engine.AgentTrustProfile` snapshot at
            the time this event was processed.
        authorization_result: Reserved for the AuthMatrix engine (not yet
            implemented).  Stored as an opaque ``dict`` to avoid coupling.
        decision_result: Final output of
            :class:`~app.core.decision_engine.DecisionEngine`.

    Example::

        event = make_event(
            agent_id="agent-99",
            message="Hello from the agent",
            requested_tool=None,
        )
        assert event.detection_result is None  # not yet enriched

    Note:
        ``metadata`` and ``authorization_result`` are stored as plain dicts
        to keep this module free of engine-specific imports at runtime.
        Typed wrappers can be added in a future sprint once AuthMatrix is
        implemented.
    """

    # ── Immutable core ────────────────────────────────────────────────────────
    event_id: str
    timestamp: datetime
    agent_id: str
    message: str
    requested_tool: Optional[str]
    metadata: dict[str, Any]

    # ── Progressive enrichment (None until set) ───────────────────────────────
    detection_result: Optional[Any] = field(default=None)     # DetectionResult
    behavior_analysis: Optional[Any] = field(default=None)    # BehaviorAnalysis
    trust_profile: Optional[Any] = field(default=None)        # AgentTrustProfile
    authorization_result: Optional[dict[str, Any]] = field(default=None)
    decision_result: Optional[Any] = field(default=None)      # DecisionResult

    # ── Derived helpers ───────────────────────────────────────────────────────

    @property
    def is_enriched(self) -> bool:
        """Return ``True`` if at least one enrichment field has been populated.

        Returns:
            bool: ``True`` when any optional enrichment field is not ``None``.
        """
        return any([
            self.detection_result is not None,
            self.behavior_analysis is not None,
            self.trust_profile is not None,
            self.authorization_result is not None,
            self.decision_result is not None,
        ])

    @property
    def is_complete(self) -> bool:
        """Return ``True`` when the event has passed through all core engines.

        "Complete" means detection, trust, and decision results are all present.
        Behavior analysis is treated as optional enrichment.

        Returns:
            bool: ``True`` when the three primary enrichments are populated.
        """
        return (
            self.detection_result is not None
            and self.trust_profile is not None
            and self.decision_result is not None
        )

    @property
    def enrichment_stage(self) -> str:
        """Return a human-readable label for the current enrichment stage.

        Useful for logging and dashboards.

        Returns:
            str: One of ``"raw"``, ``"detected"``, ``"profiled"``,
            ``"decided"``, or ``"complete"``.
        """
        if self.decision_result is not None:
            return "complete"
        if self.trust_profile is not None:
            return "profiled"
        if self.behavior_analysis is not None:
            return "behavior_analyzed"
        if self.detection_result is not None:
            return "detected"
        return "raw"

    def summary(self) -> dict[str, Any]:
        """Return a compact, serialisation-friendly summary of this event.

        Suitable for structured logging, dashboard widgets, and API responses
        that do not need the full engine output objects.

        Returns:
            dict with keys: ``event_id``, ``agent_id``, ``timestamp``,
            ``requested_tool``, ``stage``, ``is_complete``, ``has_decision``,
            ``risk_score`` (if detection is present), ``decision`` (if
            decision is present).
        """
        out: dict[str, Any] = {
            "event_id": self.event_id,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp.isoformat(),
            "requested_tool": self.requested_tool,
            "stage": self.enrichment_stage,
            "is_complete": self.is_complete,
            "has_decision": self.decision_result is not None,
        }
        if self.detection_result is not None:
            out["risk_score"] = getattr(self.detection_result, "risk_score", None)
            out["threat_count"] = getattr(self.detection_result, "threat_count", None)
        if self.decision_result is not None:
            decision = getattr(self.decision_result, "decision", None)
            out["decision"] = decision.value if hasattr(decision, "value") else str(decision)
            out["confidence"] = getattr(self.decision_result, "confidence", None)
        if self.trust_profile is not None:
            out["trust_score"] = getattr(self.trust_profile, "trust_score", None)
        if self.behavior_analysis is not None:
            level = getattr(self.behavior_analysis, "deviation_level", None)
            out["deviation_level"] = level.value if hasattr(level, "value") else str(level)
        return out


# ============================================================================
# Factory function
# ============================================================================


def make_event(
    agent_id: str,
    message: str,
    requested_tool: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    event_id: Optional[str] = None,
    timestamp: Optional[datetime] = None,
) -> SecurityEvent:
    """Create a fresh, un-enriched :class:`SecurityEvent`.

    This is the canonical entry point for creating events.  All optional
    fields are ``None``; callers enrich them progressively using
    :func:`~app.core.events.enrichment.enrich`.

    Args:
        agent_id: Unique, stable identifier of the requesting agent.
        message: Raw message text submitted by the agent.
        requested_tool: Optional capability name the agent is requesting.
        metadata: Arbitrary key-value context.  Defaults to an empty dict.
        event_id: Optional explicit event UUID (for replay / testing).
            Auto-generated when ``None``.
        timestamp: Optional explicit creation timestamp (for replay / testing).
            Defaults to ``datetime.now(timezone.utc)``.

    Returns:
        A new :class:`SecurityEvent` with all enrichment fields set to ``None``.

    Raises:
        ValueError: If *agent_id* or *message* are empty strings.

    Example::

        event = make_event(
            agent_id="agent-1",
            message="list files in /etc",
            requested_tool="file_read",
            metadata={"session": "abc"},
        )

    Note:
        TODO [REPLAY]: Accept a ``correlation_id`` parameter that links
        replayed events back to their original event chain.
    """
    if not agent_id or not agent_id.strip():
        raise ValueError("agent_id must be a non-empty string.")
    if message is None:
        raise ValueError("message must not be None.")

    return SecurityEvent(
        event_id=event_id or str(uuid.uuid4()),
        timestamp=timestamp or datetime.now(timezone.utc),
        agent_id=agent_id.strip(),
        message=message,
        requested_tool=requested_tool,
        metadata=dict(metadata) if metadata else {},
    )
