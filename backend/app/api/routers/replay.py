"""Replay router for AgentShield X API v1.

Endpoints
---------
``GET /api/v1/replay``              – List replay sessions (with filtering).
``GET /api/v1/replay/{session_id}`` – Full replay timeline for one session.

These endpoints are **read-only**.  They translate the in-memory
:class:`~app.core.replay.replay_models.ReplaySession` objects into Pydantic
response models without any side effects.

Future extension points
-----------------------
TODO [AUTH]:       Restrict replay access to authenticated users with the
                   ``analyst`` or ``admin`` role.
TODO [PAGINATION]: Add ``page`` and ``page_size`` query parameters with a
                   ``PaginatedResponse`` wrapper.
TODO [STREAM]:     Add ``GET /replay/{session_id}/stream`` that pushes frame
                   updates over SSE as they arrive in real time.
TODO [EXPORT]:     Add ``GET /replay/{session_id}/export`` that returns the
                   session as a downloadable JSON file or formatted report.
TODO [SEARCH]:     Add full-text search on ``overall_summary`` and frame
                   descriptions.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_replay_engine, require_roles
from app.api.schemas import (
    FrameItem,
    ReplayListResponse,
    ReplaySessionResponse,
    ReplaySessionSummary,
)
from app.core.replay import ReplayEngine
from app.core.replay.replay_models import ReplaySession, SessionStatus

router = APIRouter(prefix="/replay", tags=["Replay"])


# ============================================================================
# GET /replay
# ============================================================================


@router.get(
    "",
    response_model=ReplayListResponse,
    summary="List Replay Sessions",
    dependencies=[Depends(require_roles("Admin", "Security Analyst"))],
    description=(
        "Returns a list of replay sessions, optionally filtered by agent ID "
        "or session status."
    ),
)
def list_sessions(
    agent_id: Optional[str] = Query(None, description="Filter by agent identifier."),
    session_status: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by status: IN_PROGRESS | COMPLETE | FAILED.",
    ),
    limit: int = Query(50, ge=1, le=500, description="Maximum sessions to return."),
    replay_engine: ReplayEngine = Depends(get_replay_engine),
) -> ReplayListResponse:
    """Return a filtered list of replay sessions.

    Args:
        agent_id: Optional agent ID filter.
        session_status: Optional status filter string.
        limit: Maximum number of sessions to return (1–500).
        replay_engine: Injected :class:`~app.core.replay.ReplayEngine`.

    Returns:
        :class:`~app.api.schemas.ReplayListResponse`.

    Raises:
        :exc:`fastapi.HTTPException` 400: If *session_status* is not a valid
        :class:`~app.core.replay.replay_models.SessionStatus` value.
    """
    # TODO [AUTH]: Verify caller has at least the ``viewer`` role.

    parsed_status: Optional[SessionStatus] = None
    if session_status is not None:
        try:
            parsed_status = SessionStatus(session_status.upper())
        except ValueError:
            valid = [s.value for s in SessionStatus]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status {session_status!r}. Must be one of: {valid}.",
            )

    sessions = replay_engine.list_sessions(
        agent_id=agent_id,
        status=parsed_status,
        limit=limit,
    )

    summaries = [_session_to_summary(s) for s in sessions]
    return ReplayListResponse(total=len(summaries), sessions=summaries)


# ============================================================================
# GET /replay/{session_id}
# ============================================================================


@router.get(
    "/{session_id}",
    response_model=ReplaySessionResponse,
    summary="Get Replay Timeline",
    dependencies=[Depends(require_roles("Admin", "Security Analyst"))],
    description="Returns the full ordered replay timeline for a single session.",
)
def get_session(
    session_id: str,
    replay_engine: ReplayEngine = Depends(get_replay_engine),
) -> ReplaySessionResponse:
    """Return the full replay timeline for *session_id*.

    Args:
        session_id: The replay session identifier.
        replay_engine: Injected :class:`~app.core.replay.ReplayEngine`.

    Returns:
        :class:`~app.api.schemas.ReplaySessionResponse` with all frames.

    Raises:
        :exc:`fastapi.HTTPException` 404: If *session_id* is not found.
    """
    # TODO [AUTH]: Verify caller has at least the ``analyst`` role.

    session = replay_engine.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Replay session not found: {session_id!r}.",
        )

    return _session_to_full_response(session)


# ============================================================================
# Private translation helpers
# ============================================================================


def _session_to_summary(session: ReplaySession) -> ReplaySessionSummary:
    """Translate a :class:`~app.core.replay.replay_models.ReplaySession` to a
    lightweight :class:`~app.api.schemas.ReplaySessionSummary`.

    Args:
        session: Source session object.

    Returns:
        :class:`~app.api.schemas.ReplaySessionSummary`.
    """
    return ReplaySessionSummary(
        session_id=session.session_id,
        event_id=session.event_id,
        agent_id=session.agent_id,
        status=session.status.value,
        started_at=session.started_at,
        frame_count=session.frame_count,
        final_decision=session.final_decision,
        peak_risk_score=session.peak_risk_score,
    )


def _session_to_full_response(session: ReplaySession) -> ReplaySessionResponse:
    """Translate a :class:`~app.core.replay.replay_models.ReplaySession` to a
    full :class:`~app.api.schemas.ReplaySessionResponse`.

    Args:
        session: Source session object.

    Returns:
        :class:`~app.api.schemas.ReplaySessionResponse` including all frames.
    """
    frames = [
        FrameItem(
            frame_id=f.frame_id,
            stage=f.stage.value,
            timestamp=f.timestamp,
            title=f.title,
            description=f.description,
            engine=f.engine,
            risk_score=f.risk_score,
            trust_score=f.trust_score,
            decision=f.decision,
            metadata=f.metadata,
        )
        for f in session.frames
    ]

    return ReplaySessionResponse(
        session_id=session.session_id,
        event_id=session.event_id,
        agent_id=session.agent_id,
        status=session.status.value,
        started_at=session.started_at,
        completed_at=session.completed_at,
        overall_summary=session.overall_summary,
        frame_count=session.frame_count,
        duration_ms=session.duration_ms,
        final_decision=session.final_decision,
        peak_risk_score=session.peak_risk_score,
        stages_completed=[s.value for s in session.stages_completed],
        frames=frames,
    )
