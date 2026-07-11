"""Data models for the AgentShield X Attack Replay Engine.

This module owns the complete data contract for the replay subsystem.  No
business logic lives here — only typed, immutable dataclasses that carry
the information needed to reconstruct how a single AI agent request moved
through every security engine.

Design principles
-----------------
* **Immutable frames** – once a :class:`ReplayFrame` is recorded it is never
  mutated.  This makes replay sessions safe to share across threads and trivial
  to serialise.
* **Loose coupling** – the models carry only primitive types and plain dicts so
  they can be serialised to JSON / persisted to any store without depending on
  the upstream engine result types.
* **Ordered timeline** – a :class:`ReplaySession` holds an ordered list of
  :class:`ReplayFrame` objects that map exactly onto the enrichment stages of
  the :class:`~app.core.events.schema.SecurityEvent` it was built from.

Stage naming convention
-----------------------
``ReplayStage`` values intentionally mirror the six enrichment stages defined
in :class:`~app.core.events.lifecycle.EventStage` plus a dedicated ``AUDITED``
terminal stage for future audit-log integration::

    RECEIVED  →  DETECTED  →  BEHAVIOR_ANALYZED  →  TRUST_UPDATED
                 →  DECISION_MADE  →  AUDITED

Future extension points
-----------------------
TODO [LIVE_REPLAY]:    Add a ``ReplayCommand`` model (PLAY / PAUSE / SEEK /
                       STOP) for live interactive playback.
TODO [INCIDENT_RPT]:   Add a ``ReplayReport`` dataclass wrapping a
                       ``ReplaySession`` with analyst notes and MITRE mappings.
TODO [COMPRESSION]:    Add a ``CompressedSession`` model for long multi-event
                       timelines where adjacent identical frames are collapsed.
TODO [MULTI_EVENT]:    Add a ``MultiEventReplay`` container that sequences
                       several ``ReplaySession`` objects for attack-chain
                       reconstruction.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


# ============================================================================
# Enumerations
# ============================================================================


class ReplayStage(str, Enum):
    """Canonical stage labels for a :class:`ReplayFrame`.

    Each value represents one discrete step in the security processing
    pipeline.  Stages are ordered from least to most processed.

    Attributes:
        RECEIVED: Raw event received; no engine has run yet.
        DETECTED: Detection Engine has analysed the message.
        BEHAVIOR_ANALYZED: Behavioral DNA Engine has scored the observation.
        TRUST_UPDATED: Trust Engine has evaluated / updated the agent profile.
        DECISION_MADE: Decision Engine has produced a final verdict.
        AUDITED: Audit log entry has been written (future).
    """

    RECEIVED = "RECEIVED"
    DETECTED = "DETECTED"
    BEHAVIOR_ANALYZED = "BEHAVIOR_ANALYZED"
    TRUST_UPDATED = "TRUST_UPDATED"
    DECISION_MADE = "DECISION_MADE"
    AUDITED = "AUDITED"

    @property
    def order(self) -> int:
        """Return the canonical processing order of this stage (0-indexed).

        Returns:
            int: Position in the pipeline (lower = earlier).
        """
        _ORDER: dict[str, int] = {
            "RECEIVED": 0,
            "DETECTED": 1,
            "BEHAVIOR_ANALYZED": 2,
            "TRUST_UPDATED": 3,
            "DECISION_MADE": 4,
            "AUDITED": 5,
        }
        return _ORDER.get(self.value, 99)

    def __lt__(self, other: ReplayStage) -> bool:  # noqa: D105
        return self.order < other.order

    def __le__(self, other: ReplayStage) -> bool:  # noqa: D105
        return self.order <= other.order


class SessionStatus(str, Enum):
    """Lifecycle status of a :class:`ReplaySession`.

    Attributes:
        IN_PROGRESS: Frames are still being added; session is open.
        COMPLETE: All expected frames have been recorded; session is closed.
        FAILED: Session was aborted due to an error mid-pipeline.
    """

    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


# ============================================================================
# ReplayFrame — one discrete pipeline step
# ============================================================================


@dataclass(frozen=True)
class ReplayFrame:
    """An immutable snapshot of one discrete step in the security pipeline.

    A frame is the atomic unit of a replay timeline.  It captures both what
    the engine *received* (input summary) and what it *produced* (output
    summary) so that a full reconstruction can be made without access to the
    live engines.

    Attributes:
        frame_id: Unique identifier for this frame (UUID4 string).
        stage: The :class:`ReplayStage` this frame represents.
        timestamp: UTC time when this frame was recorded.
        title: Short human-readable label (e.g. ``"Threat Detection"``).
        description: One-sentence explanation of what happened in this stage.
        engine: Name of the engine that produced this frame
            (e.g. ``"DetectionEngine"``).  ``"system"`` for synthetic frames.
        risk_score: Risk score at this stage, or ``None`` if not yet known.
        trust_score: Agent trust score at this stage, or ``None`` if not yet
            known.
        decision: Decision value string (e.g. ``"BLOCK"``) or ``None``.
        metadata: Arbitrary engine-specific detail (reason codes, threat
            names, deviation level, etc.).  Always a plain dict for easy
            JSON serialisation.

    Example::

        frame = ReplayFrame(
            frame_id=str(uuid.uuid4()),
            stage=ReplayStage.DETECTED,
            timestamp=datetime.now(timezone.utc),
            title="Threat Detection",
            description="2 threat patterns detected; risk score 0.85.",
            engine="DetectionEngine",
            risk_score=0.85,
            trust_score=None,
            decision=None,
            metadata={"threat_count": 2, "categories": ["command_injection"]},
        )
    """

    frame_id: str
    stage: ReplayStage
    timestamp: datetime
    title: str
    description: str
    engine: str
    risk_score: Optional[float]
    trust_score: Optional[float]
    decision: Optional[str]
    metadata: dict[str, Any]


# ============================================================================
# ReplaySession — the full ordered timeline for one event
# ============================================================================


@dataclass
class ReplaySession:
    """A complete, ordered replay timeline for a single :class:`~app.core.events.schema.SecurityEvent`.

    A session is created by :meth:`~app.core.replay.replay_engine.ReplayEngine.create_session`
    and progressively populated with :class:`ReplayFrame` objects — one per
    pipeline stage — until it is closed by
    :meth:`~app.core.replay.replay_engine.ReplayEngine.complete_session`.

    Attributes:
        session_id: Unique identifier for this replay session (UUID4 string).
        event_id: The ``event_id`` of the originating
            :class:`~app.core.events.schema.SecurityEvent`.
        agent_id: Agent identifier copied from the source event for quick
            filtering without deserialising frames.
        frames: Ordered list of :class:`ReplayFrame` objects recorded so far.
            The list is in chronological order (earliest first).
        started_at: UTC timestamp when the session was created.
        completed_at: UTC timestamp when :meth:`~app.core.replay.replay_engine.ReplayEngine.complete_session`
            was called, or ``None`` if the session is still in progress.
        status: Current :class:`SessionStatus`.
        overall_summary: A brief human-readable summary written when the session
            is completed (e.g. ``"Agent blocked after 2 threats detected"``).
        schema_version: Version string for forward-compatibility.  Increment
            this when the serialisation format changes.

    Example::

        session = ReplaySession(
            session_id=str(uuid.uuid4()),
            event_id="evt-001",
            agent_id="agent-42",
        )
        print(session.frame_count)   # 0
        print(session.duration_ms)   # None  (not complete yet)
    """

    session_id: str
    event_id: str
    agent_id: str
    frames: list[ReplayFrame] = field(default_factory=list)
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    completed_at: Optional[datetime] = field(default=None)
    status: SessionStatus = field(default=SessionStatus.IN_PROGRESS)
    overall_summary: str = field(default="")
    schema_version: str = field(default="1.0")

    # ── Derived helpers ───────────────────────────────────────────────────────

    @property
    def frame_count(self) -> int:
        """Return the number of frames recorded in this session.

        Returns:
            int: Total frame count.
        """
        return len(self.frames)

    @property
    def duration_ms(self) -> Optional[float]:
        """Return the session duration in milliseconds, or ``None`` if open.

        Returns:
            float: Elapsed milliseconds from :attr:`started_at` to
            :attr:`completed_at`, or ``None`` when the session is still in
            progress.
        """
        if self.completed_at is None:
            return None
        delta = self.completed_at - self.started_at
        return delta.total_seconds() * 1000.0

    @property
    def final_decision(self) -> Optional[str]:
        """Return the decision value from the last ``DECISION_MADE`` frame.

        Iterates frames in reverse order so the most recent decision is
        returned if multiple decision frames exist.

        Returns:
            Optional[str]: Decision string (e.g. ``"BLOCK"``) or ``None``.
        """
        for frame in reversed(self.frames):
            if frame.stage == ReplayStage.DECISION_MADE and frame.decision:
                return frame.decision
        return None

    @property
    def peak_risk_score(self) -> Optional[float]:
        """Return the highest risk score observed across all frames.

        Returns:
            Optional[float]: Maximum risk score or ``None`` if no frame
            carries a risk score.
        """
        scores = [f.risk_score for f in self.frames if f.risk_score is not None]
        return max(scores) if scores else None

    @property
    def stages_completed(self) -> list[ReplayStage]:
        """Return a sorted list of all unique stages present in the timeline.

        Returns:
            list[ReplayStage]: Unique stages in canonical pipeline order.
        """
        return sorted({f.stage for f in self.frames})

    def frame_at_stage(self, stage: ReplayStage) -> Optional[ReplayFrame]:
        """Return the first frame matching *stage*, or ``None``.

        Args:
            stage: The :class:`ReplayStage` to look up.

        Returns:
            :class:`ReplayFrame` or ``None`` if the stage has not been
            recorded yet.
        """
        for frame in self.frames:
            if frame.stage == stage:
                return frame
        return None


# ============================================================================
# Factory helpers
# ============================================================================


def make_session(event_id: str, agent_id: str) -> ReplaySession:
    """Create a fresh, empty :class:`ReplaySession`.

    Args:
        event_id: ``event_id`` of the originating
            :class:`~app.core.events.schema.SecurityEvent`.
        agent_id: Agent identifier from the source event.

    Returns:
        A new :class:`ReplaySession` with status ``IN_PROGRESS`` and no frames.

    Raises:
        ValueError: If *event_id* or *agent_id* are empty strings.

    Example::

        session = make_session("evt-001", "agent-42")
        assert session.status == SessionStatus.IN_PROGRESS
    """
    if not event_id or not event_id.strip():
        raise ValueError("event_id must be a non-empty string.")
    if not agent_id or not agent_id.strip():
        raise ValueError("agent_id must be a non-empty string.")
    return ReplaySession(
        session_id=str(uuid.uuid4()),
        event_id=event_id.strip(),
        agent_id=agent_id.strip(),
    )


def make_frame(
    stage: ReplayStage,
    title: str,
    description: str,
    engine: str,
    *,
    risk_score: Optional[float] = None,
    trust_score: Optional[float] = None,
    decision: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    timestamp: Optional[datetime] = None,
) -> ReplayFrame:
    """Create a :class:`ReplayFrame` with a generated ``frame_id``.

    Args:
        stage: The :class:`ReplayStage` this frame captures.
        title: Short human-readable label for the stage.
        description: One-sentence explanation of what happened.
        engine: Name of the engine that produced this frame.
        risk_score: Optional risk score at this point in the pipeline.
        trust_score: Optional agent trust score at this point.
        decision: Optional decision string (e.g. ``"BLOCK"``).
        metadata: Optional dict of engine-specific details.
        timestamp: Optional explicit timestamp (defaults to now UTC).

    Returns:
        A new, immutable :class:`ReplayFrame`.

    Example::

        frame = make_frame(
            stage=ReplayStage.DETECTED,
            title="Threat Detection",
            description="Command injection detected.",
            engine="DetectionEngine",
            risk_score=0.92,
            metadata={"threat_count": 1},
        )
    """
    return ReplayFrame(
        frame_id=str(uuid.uuid4()),
        stage=stage,
        timestamp=timestamp or datetime.now(timezone.utc),
        title=title,
        description=description,
        engine=engine,
        risk_score=risk_score,
        trust_score=trust_score,
        decision=decision,
        metadata=dict(metadata) if metadata else {},
    )
