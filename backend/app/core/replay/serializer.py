"""Replay session serialiser for the AgentShield X Attack Replay Engine.

This module converts :class:`~app.core.replay.replay_models.ReplaySession`
objects into JSON-ready structures.  It is deliberately a thin, dependency-free
translation layer with no business logic.

Serialisation contract
----------------------
The output of :func:`session_to_dict` is a plain Python ``dict`` containing
only the following primitive types: ``str``, ``int``, ``float``, ``bool``,
``None``, ``list``, ``dict``.  This means it can be passed directly to
``json.dumps`` without a custom encoder.

Datetime values are serialised as ISO-8601 strings (UTC).
Enum values are serialised as their ``.value`` strings.

Round-trip support
------------------
:func:`session_from_dict` reconstructs a :class:`~app.core.replay.replay_models.ReplaySession`
from a previously serialised dict.  This enables:

* Storing sessions in a file / object-store and reloading them later.
* Sending sessions over HTTP APIs without a shared-memory dependency.
* Writing deterministic test fixtures.

Future extension points
-----------------------
TODO [LIVE_REPLAY]:    Add a ``stream_frames`` generator that emits frame
                       dicts one at a time for server-sent event (SSE) or
                       WebSocket streaming.
TODO [PLAYBACK]:       Add a ``seek_to_stage`` helper that slices the frame
                       list to a given :class:`~app.core.replay.replay_models.ReplayStage`
                       for interactive playback controls.
TODO [VIDEO_EXPORT]:   Add an ``export_to_svg`` / ``export_to_html`` renderer
                       that converts a session into a visual timeline artifact.
TODO [INCIDENT_RPT]:   Add a ``to_markdown_report`` serialiser that produces a
                       structured incident-report document from a session.
TODO [COMPRESSION]:    Add a ``compress_session`` helper that merges adjacent
                       NORMAL/ALLOW frames to reduce payload size for long
                       multi-event replays.
TODO [MULTI_EVENT]:    Add a ``sessions_to_dict`` helper for serialising a
                       list of sessions (attack-chain replay).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from app.core.replay.replay_models import (
    ReplayFrame,
    ReplaySession,
    ReplayStage,
    SessionStatus,
    make_frame,
    make_session,
)


# ============================================================================
# Serialisation helpers
# ============================================================================


def _dt_to_iso(dt: Optional[datetime]) -> Optional[str]:
    """Serialise *dt* to an ISO-8601 string, or ``None`` if *dt* is ``None``.

    Args:
        dt: Datetime to serialise.

    Returns:
        str | None: ISO-8601 string (UTC) or ``None``.
    """
    return dt.isoformat() if dt is not None else None


def _dt_from_iso(s: Optional[str]) -> Optional[datetime]:
    """Parse *s* as an ISO-8601 datetime string, or return ``None``.

    Args:
        s: ISO-8601 string or ``None``.

    Returns:
        datetime | None: Parsed UTC datetime or ``None``.
    """
    if s is None:
        return None
    return datetime.fromisoformat(s)


# ============================================================================
# Frame serialisation
# ============================================================================


def frame_to_dict(frame: ReplayFrame) -> dict[str, Any]:
    """Serialise a :class:`~app.core.replay.replay_models.ReplayFrame` to a dict.

    All values are JSON-primitive-safe.

    Args:
        frame: The frame to serialise.

    Returns:
        dict[str, Any]: Serialisable representation of the frame.

    Example::

        d = frame_to_dict(frame)
        assert d["stage"] == "DETECTED"
    """
    return {
        "frame_id": frame.frame_id,
        "stage": frame.stage.value,
        "timestamp": _dt_to_iso(frame.timestamp),
        "title": frame.title,
        "description": frame.description,
        "engine": frame.engine,
        "risk_score": frame.risk_score,
        "trust_score": frame.trust_score,
        "decision": frame.decision,
        "metadata": frame.metadata,
    }


def frame_from_dict(d: dict[str, Any]) -> ReplayFrame:
    """Reconstruct a :class:`~app.core.replay.replay_models.ReplayFrame` from
    a previously serialised dict.

    Args:
        d: Dict produced by :func:`frame_to_dict`.

    Returns:
        :class:`~app.core.replay.replay_models.ReplayFrame`.

    Raises:
        KeyError: If a required key is missing from *d*.
        ValueError: If the stage value is not a valid :class:`~app.core.replay.replay_models.ReplayStage`.
    """
    return ReplayFrame(
        frame_id=d["frame_id"],
        stage=ReplayStage(d["stage"]),
        timestamp=_dt_from_iso(d.get("timestamp")) or datetime.now(timezone.utc),
        title=d["title"],
        description=d["description"],
        engine=d["engine"],
        risk_score=d.get("risk_score"),
        trust_score=d.get("trust_score"),
        decision=d.get("decision"),
        metadata=dict(d.get("metadata") or {}),
    )



# ============================================================================
# Session serialisation
# ============================================================================


def session_to_dict(session: ReplaySession) -> dict[str, Any]:
    """Serialise a :class:`~app.core.replay.replay_models.ReplaySession` to a dict.

    The output is a flat, JSON-primitive-safe representation that can be
    passed directly to ``json.dumps``.

    Args:
        session: The session to serialise.

    Returns:
        dict[str, Any]: Full session representation including all frames,
        derived metrics, and session-level metadata.

    Example::

        d = session_to_dict(session)
        raw_json = json.dumps(d, indent=2)
    """
    return {
        # ── Identity ────────────────────────────────────────────────────────
        "session_id": session.session_id,
        "event_id": session.event_id,
        "agent_id": session.agent_id,
        "schema_version": session.schema_version,
        # ── Lifecycle ────────────────────────────────────────────────────────
        "status": session.status.value,
        "started_at": _dt_to_iso(session.started_at),
        "completed_at": _dt_to_iso(session.completed_at),
        "overall_summary": session.overall_summary,
        # ── Frames ───────────────────────────────────────────────────────────
        "frame_count": session.frame_count,
        "frames": [frame_to_dict(f) for f in session.frames],
        # ── Derived metrics ──────────────────────────────────────────────────
        "duration_ms": session.duration_ms,
        "final_decision": session.final_decision,
        "peak_risk_score": session.peak_risk_score,
        "stages_completed": [s.value for s in session.stages_completed],
    }


def session_from_dict(d: dict[str, Any]) -> ReplaySession:
    """Reconstruct a :class:`~app.core.replay.replay_models.ReplaySession` from
    a previously serialised dict.

    Args:
        d: Dict produced by :func:`session_to_dict`.

    Returns:
        :class:`~app.core.replay.replay_models.ReplaySession` with all frames
        and lifecycle state restored.

    Raises:
        KeyError: If a required key is missing from *d*.

    Example::

        session = session_from_dict(json.loads(raw_json))
        assert session.session_id == original.session_id
    """
    session = make_session(event_id=d["event_id"], agent_id=d["agent_id"])
    # Overwrite auto-generated fields with the persisted values.
    session.session_id = d["session_id"]
    session.started_at = _dt_from_iso(d["started_at"]) or session.started_at
    session.completed_at = _dt_from_iso(d.get("completed_at"))
    session.status = SessionStatus(d.get("status", SessionStatus.IN_PROGRESS.value))
    session.overall_summary = d.get("overall_summary", "")
    session.schema_version = d.get("schema_version", "1.0")
    session.frames = [frame_from_dict(f) for f in d.get("frames", [])]
    return session


# ============================================================================
# JSON entry points
# ============================================================================


def session_to_json(session: ReplaySession, indent: int = 2) -> str:
    """Serialise a :class:`~app.core.replay.replay_models.ReplaySession` to a
    JSON string.

    Args:
        session: The session to serialise.
        indent: Number of spaces to use for JSON indentation.  ``0``
            produces compact single-line output.

    Returns:
        str: Pretty-printed (or compact) JSON string.

    Example::

        json_str = session_to_json(session)
        print(json_str[:200])
    """
    indent_arg: Optional[int] = indent if indent > 0 else None
    return json.dumps(session_to_dict(session), indent=indent_arg, ensure_ascii=False)


def session_from_json(raw: str) -> ReplaySession:
    """Deserialise a JSON string into a :class:`~app.core.replay.replay_models.ReplaySession`.

    Args:
        raw: JSON string produced by :func:`session_to_json`.

    Returns:
        :class:`~app.core.replay.replay_models.ReplaySession`.

    Raises:
        json.JSONDecodeError: If *raw* is not valid JSON.
        KeyError: If a required field is missing.

    Example::

        session = session_from_json(json_str)
        assert session.status == SessionStatus.COMPLETE
    """
    return session_from_dict(json.loads(raw))
