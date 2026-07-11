"""AgentShield X — Attack Replay Engine package.

This sub-package provides a complete framework for reconstructing how a single
AI agent request moved through every security engine in the platform.

It is NOT a logging system.  Replay sessions are live, structured objects that
preserve the full enrichment history of a
:class:`~app.core.events.schema.SecurityEvent` as an ordered, inspectable
timeline of :class:`~app.core.replay.replay_models.ReplayFrame` objects.

Sub-modules
-----------
:mod:`app.core.replay.replay_models`
    All data contracts: :class:`~app.core.replay.replay_models.ReplayFrame`,
    :class:`~app.core.replay.replay_models.ReplaySession`,
    :class:`~app.core.replay.replay_models.ReplayStage`,
    :class:`~app.core.replay.replay_models.SessionStatus`, and the factory
    helpers :func:`~app.core.replay.replay_models.make_frame` /
    :func:`~app.core.replay.replay_models.make_session`.

:mod:`app.core.replay.replay_engine`
    The :class:`~app.core.replay.replay_engine.ReplayEngine` — thread-safe
    stateful registry for sessions (create / add_frame / complete / query).

:mod:`app.core.replay.timeline`
    The :class:`~app.core.replay.timeline.TimelineBuilder` — stateless
    converter from a :class:`~app.core.events.schema.SecurityEvent` to an
    ordered list of :class:`~app.core.replay.replay_models.ReplayFrame`
    objects.

:mod:`app.core.replay.serializer`
    JSON serialisation / deserialisation helpers:
    :func:`~app.core.replay.serializer.session_to_json`,
    :func:`~app.core.replay.serializer.session_from_json`,
    :func:`~app.core.replay.serializer.session_to_dict`,
    :func:`~app.core.replay.serializer.session_from_dict`.

Quickstart::

    from app.core.replay import (
        ReplayEngine,
        TimelineBuilder,
        ReplaySession,
        ReplayFrame,
        ReplayStage,
        SessionStatus,
        session_to_json,
        session_from_json,
    )
    from app.core.events import make_event, enrich

    # 1. Build a SecurityEvent (normally done in your request pipeline)
    event = make_event(agent_id="agent-1", message="rm -rf /")
    # ... enrich with engine outputs ...

    # 2. Build a replay timeline from the enriched event
    builder = TimelineBuilder()
    engine  = ReplayEngine()

    session = engine.create_session(event.event_id, event.agent_id)
    for frame in builder.build(event):
        engine.add_frame(session.session_id, frame)
    session = engine.complete_session(
        session.session_id,
        TimelineBuilder.generate_summary(event),
    )

    # 3. Inspect the timeline
    print(session.final_decision)       # "BLOCK"
    print(session.frame_count)          # 4
    print(session.duration_ms)          # e.g. 3.14

    # 4. Export to JSON
    json_str = session_to_json(session)
    restored = session_from_json(json_str)
    assert restored.session_id == session.session_id
"""

from app.core.replay.replay_engine import ReplayEngine
from app.core.replay.replay_models import (
    ReplayFrame,
    ReplaySession,
    ReplayStage,
    SessionStatus,
    make_frame,
    make_session,
)
from app.core.replay.serializer import (
    frame_from_dict,
    frame_to_dict,
    session_from_dict,
    session_from_json,
    session_to_dict,
    session_to_json,
)
from app.core.replay.timeline import TimelineBuilder

__all__ = [
    # ── Engine ────────────────────────────────────────────────────────────────
    "ReplayEngine",
    # ── Timeline builder ─────────────────────────────────────────────────────
    "TimelineBuilder",
    # ── Models ────────────────────────────────────────────────────────────────
    "ReplayFrame",
    "ReplaySession",
    "ReplayStage",
    "SessionStatus",
    "make_frame",
    "make_session",
    # ── Serialiser ────────────────────────────────────────────────────────────
    "session_to_json",
    "session_from_json",
    "session_to_dict",
    "session_from_dict",
    "frame_to_dict",
    "frame_from_dict",
]
