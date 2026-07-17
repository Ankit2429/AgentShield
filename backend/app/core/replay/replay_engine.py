"""Attack Replay Engine for AgentShield.

The :class:`ReplayEngine` is the **stateful registry** for all replay
sessions.  It manages the lifecycle of :class:`~app.core.replay.replay_models.ReplaySession`
objects: creation, frame accumulation, completion, and retrieval.

This engine is deliberately **not responsible** for interpreting
:class:`~app.core.events.schema.SecurityEvent` objects — that translation
responsibility belongs to :mod:`app.core.replay.timeline`.  The Replay Engine
only stores and manages what the Timeline Builder produces.

Architecture overview
---------------------
::

    SecurityEvent ──► TimelineBuilder.build()   ← timeline.py
                           │
                           ▼
                    ReplaySession + ReplayFrames
                           │
                           ▼
                     ReplayEngine                ← this module
                     ├── create_session()
                     ├── add_frame()
                     ├── complete_session()
                     ├── get_session()
                     └── list_sessions()
                           │
                           ▼
                      ReplaySerializer          ← serializer.py
                      └── to_json() / to_dict()

Thread safety
-------------
A :class:`threading.RLock` serialises all mutations.  Read operations
(``get_session``, ``list_sessions``) hold the lock to return consistent
snapshots.

Storage migration
-----------------
Replace :meth:`_store_session`, :meth:`_fetch_session`, and
:meth:`_fetch_all` to migrate from in-memory to a persistent store (Redis,
Postgres, S3, etc.) without touching any other code.

Future extension points
-----------------------
TODO [LIVE_REPLAY]:   Emit frame events to a pub/sub channel so live
                      dashboards can stream the replay in real time.
TODO [PLAYBACK]:      Add ``seek(session_id, stage)`` and ``rewind()``
                      controls backed by a playback cursor per session.
TODO [VIDEO_EXPORT]:  Integrate with a rendering service to convert a
                      completed session into an annotated video artifact.
TODO [PERSISTENCE]:   Replace in-memory dict with a durable session store
                      (e.g. Redis Streams, DynamoDB, TimescaleDB).
TODO [RETENTION]:     Add a TTL / eviction policy so old sessions are
                      automatically pruned from memory.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Optional

from app.core.replay.replay_models import (
    ReplayFrame,
    ReplaySession,
    ReplayStage,
    SessionStatus,
    make_session,
)


# ============================================================================
# Tunable constants
# ============================================================================

# Maximum number of sessions to keep in memory before the oldest is evicted.
# TODO [RETENTION]: Replace this with a TTL-based eviction policy.
_MAX_SESSIONS: int = 1000


# ============================================================================
# ReplayEngine
# ============================================================================


class ReplayEngine:
    """Stateful registry for :class:`~app.core.replay.replay_models.ReplaySession` objects.

    The engine manages the full lifecycle of a replay session: creation,
    incremental frame accumulation, completion, and retrieval.

    It is deliberately **storage-agnostic** — the three private helpers
    (:meth:`_store_session`, :meth:`_fetch_session`, :meth:`_fetch_all`)
    are the only points that touch the backing store.

    Singleton usage::

        replay_engine = ReplayEngine()   # instantiate once at startup

    Example::

        engine = ReplayEngine()

        session = engine.create_session(event_id="evt-001", agent_id="agent-1")

        engine.add_frame(session.session_id, received_frame)
        engine.add_frame(session.session_id, detection_frame)

        session = engine.complete_session(session.session_id, "Agent blocked.")
        assert session.status == SessionStatus.COMPLETE
    """

    def __init__(self) -> None:
        """Initialise the engine with an empty in-memory session store."""
        # TODO [PERSISTENCE]: Replace with a durable session store.
        self._sessions: dict[str, ReplaySession] = {}
        self._insertion_order: list[str] = []   # For LRU eviction tracking.
        self._lock: threading.RLock = threading.RLock()

    # =========================================================================
    # Public API
    # =========================================================================

    def create_session(self, event_id: str, agent_id: str) -> ReplaySession:
        """Create and register a new :class:`~app.core.replay.replay_models.ReplaySession`.

        The session begins with status ``IN_PROGRESS`` and zero frames.

        Args:
            event_id: ``event_id`` of the originating
                :class:`~app.core.events.schema.SecurityEvent`.
            agent_id: Agent identifier from the source event.

        Returns:
            The newly created :class:`~app.core.replay.replay_models.ReplaySession`.

        Raises:
            ValueError: If *event_id* or *agent_id* are empty strings.

        Example::

            session = engine.create_session("evt-001", "agent-42")
            assert session.status == SessionStatus.IN_PROGRESS
        """
        session = make_session(event_id, agent_id)
        with self._lock:
            self._evict_if_needed()
            self._store_session(session)
        return session

    def add_frame(
        self,
        session_id: str,
        frame: ReplayFrame,
    ) -> ReplaySession:
        """Append *frame* to the named session and return the updated session.

        Frames may be added in any order; they are stored in the order they
        arrive.  The :class:`~app.core.replay.timeline.TimelineBuilder`
        always produces frames in canonical pipeline order.

        Args:
            session_id: The ``session_id`` of the target session.
            frame: The :class:`~app.core.replay.replay_models.ReplayFrame`
                to append.

        Returns:
            The updated :class:`~app.core.replay.replay_models.ReplaySession`.

        Raises:
            KeyError: If *session_id* is not found.
            RuntimeError: If the session is already ``COMPLETE`` or ``FAILED``.

        Example::

            engine.add_frame(session.session_id, detection_frame)
        """
        with self._lock:
            session = self._require_session(session_id)
            if session.status != SessionStatus.IN_PROGRESS:
                raise RuntimeError(
                    f"Cannot add frame to session {session_id!r} "
                    f"with status {session.status.value!r}."
                )
            session.frames.append(frame)
            # TODO [LIVE_REPLAY]: Publish frame to a pub/sub channel here.
            return session

    def complete_session(
        self,
        session_id: str,
        overall_summary: str = "",
    ) -> ReplaySession:
        """Close the session, set its status to ``COMPLETE``, and record the summary.

        Args:
            session_id: The ``session_id`` of the session to complete.
            overall_summary: Human-readable summary of what happened
                (e.g. ``"Agent blocked after command injection detected"``).

        Returns:
            The completed :class:`~app.core.replay.replay_models.ReplaySession`.

        Raises:
            KeyError: If *session_id* is not found.
            RuntimeError: If the session is already ``COMPLETE`` or ``FAILED``.

        Example::

            session = engine.complete_session(session.session_id, "Agent blocked.")
            assert session.status == SessionStatus.COMPLETE
        """
        with self._lock:
            session = self._require_session(session_id)
            if session.status != SessionStatus.IN_PROGRESS:
                raise RuntimeError(
                    f"Session {session_id!r} is already {session.status.value!r}."
                )
            session.completed_at = datetime.now(timezone.utc)
            session.status = SessionStatus.COMPLETE
            session.overall_summary = overall_summary
            # TODO [VIDEO_EXPORT]: Trigger async video-export job here.
            return session

    def fail_session(
        self,
        session_id: str,
        reason: str = "",
    ) -> ReplaySession:
        """Mark a session as ``FAILED`` (e.g. pipeline errored mid-way).

        Args:
            session_id: The ``session_id`` to mark as failed.
            reason: Human-readable failure reason stored in ``overall_summary``.

        Returns:
            The updated :class:`~app.core.replay.replay_models.ReplaySession`.

        Raises:
            KeyError: If *session_id* is not found.
        """
        with self._lock:
            session = self._require_session(session_id)
            session.completed_at = datetime.now(timezone.utc)
            session.status = SessionStatus.FAILED
            session.overall_summary = reason or "Session failed."
            return session

    def get_session(self, session_id: str) -> Optional[ReplaySession]:
        """Return the session with *session_id*, or ``None`` if not found.

        Args:
            session_id: Session identifier to look up.

        Returns:
            :class:`~app.core.replay.replay_models.ReplaySession` or ``None``.

        Example::

            session = engine.get_session("sess-abc")
        """
        with self._lock:
            return self._fetch_session(session_id)

    def list_sessions(
        self,
        agent_id: Optional[str] = None,
        status: Optional[SessionStatus] = None,
        limit: int = 100,
    ) -> list[ReplaySession]:
        """Return a filtered, capped list of sessions.

        Args:
            agent_id: If given, return only sessions for this agent.
            status: If given, return only sessions with this
                :class:`~app.core.replay.replay_models.SessionStatus`.
            limit: Maximum number of sessions to return.  Defaults to 100.

        Returns:
            list[ReplaySession]: Matching sessions, most-recently-started
            first.

        Example::

            # All complete sessions for agent-42 (newest first)
            sessions = engine.list_sessions(
                agent_id="agent-42",
                status=SessionStatus.COMPLETE,
            )
        """
        with self._lock:
            all_sessions = list(self._fetch_all())

        # Sort newest first.
        all_sessions.sort(key=lambda s: s.started_at, reverse=True)

        if agent_id is not None:
            all_sessions = [s for s in all_sessions if s.agent_id == agent_id]
        if status is not None:
            all_sessions = [s for s in all_sessions if s.status == status]

        return all_sessions[:limit]

    @property
    def session_count(self) -> int:
        """Return the total number of sessions currently held in memory.

        Returns:
            int: Session count.
        """
        with self._lock:
            return len(self._sessions)

    # =========================================================================
    # Storage helpers — replace to migrate to a persistent store
    # =========================================================================

    def _store_session(self, session: ReplaySession) -> None:
        """Persist *session* to the backing store (upsert semantics).

        Args:
            session: Session to save.

        Note:
            TODO [PERSISTENCE]: Replace with an async upsert to the configured
            durable store.
        """
        if session.session_id not in self._sessions:
            self._insertion_order.append(session.session_id)
        self._sessions[session.session_id] = session

    def _fetch_session(self, session_id: str) -> Optional[ReplaySession]:
        """Retrieve a session from the backing store.

        Args:
            session_id: Session identifier.

        Returns:
            :class:`~app.core.replay.replay_models.ReplaySession` or ``None``.
        """
        return self._sessions.get(session_id)

    def _fetch_all(self):
        """Yield every stored session.

        Yields:
            :class:`~app.core.replay.replay_models.ReplaySession` instances.
        """
        yield from self._sessions.values()

    # =========================================================================
    # Private helpers
    # =========================================================================

    def _require_session(self, session_id: str) -> ReplaySession:
        """Return the session or raise :exc:`KeyError` if missing.

        Args:
            session_id: Session identifier.

        Returns:
            :class:`~app.core.replay.replay_models.ReplaySession`.

        Raises:
            KeyError: If *session_id* is not registered.
        """
        session = self._fetch_session(session_id)
        if session is None:
            raise KeyError(f"Replay session not found: {session_id!r}")
        return session

    def _evict_if_needed(self) -> None:
        """Evict the oldest session when :data:`_MAX_SESSIONS` is exceeded.

        Called while the lock is held, immediately before storing a new
        session.

        Note:
            TODO [RETENTION]: Replace this simple FIFO eviction with a
            configurable TTL-based expiry policy.
        """
        while len(self._sessions) >= _MAX_SESSIONS and self._insertion_order:
            oldest_id = self._insertion_order.pop(0)
            self._sessions.pop(oldest_id, None)
