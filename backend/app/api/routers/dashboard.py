"""Dashboard router for AgentShield X API v1.

Endpoint
--------
``GET /api/v1/dashboard``

Returns a live operational snapshot aggregated from all engine singletons:

* Active agent count (from TrustEngine)
* Session counts broken down by threat / blocked status (from ReplayEngine)
* Average trust score across all known agents
* Up to 10 most recent completed decisions

All aggregation happens at request time from in-memory state.  No caching is
applied — every call returns a fresh snapshot.

Future extension points
-----------------------
TODO [CACHE]:       Add a short TTL cache (e.g. 5 s) to reduce CPU overhead
                    when the dashboard is polled by multiple clients.
TODO [AUTH]:        Restrict to authenticated callers.
TODO [WEBSOCKET]:   Add ``WS /dashboard/live`` for push-based live dashboard
                    updates without polling.
TODO [TIME_RANGE]:  Add ``?since=`` and ``?until=`` query parameters to scope
                    metrics to a specific time window.
TODO [EXPORT]:      Add ``GET /dashboard/export`` that returns a CSV/JSON
                    snapshot for reporting.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_replay_engine, get_trust_engine
from app.api.schemas import DashboardResponse, RecentDecisionItem
from app.core.replay import ReplayEngine
from app.core.replay.replay_models import SessionStatus
from app.core.trust_engine import TrustEngine

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# ============================================================================
# GET /dashboard
# ============================================================================


@router.get(
    "",
    response_model=DashboardResponse,
    summary="Operational Dashboard Summary",
    description=(
        "Returns a live snapshot: active agents, session statistics, "
        "average trust score, and the 10 most recent security decisions."
    ),
)
def get_dashboard(
    trust_engine: TrustEngine = Depends(get_trust_engine),
    replay_engine: ReplayEngine = Depends(get_replay_engine),
) -> DashboardResponse:
    """Return the operational dashboard summary.

    Args:
        trust_engine: Injected :class:`~app.core.trust_engine.TrustEngine`.
        replay_engine: Injected :class:`~app.core.replay.ReplayEngine`.

    Returns:
        :class:`~app.api.schemas.DashboardResponse`.
    """
    # TODO [AUTH]: Verify caller identity.
    # TODO [CACHE]: Return a cached snapshot if fresher than 5 s.

    # ── Agent metrics ─────────────────────────────────────────────────────────
    all_profiles = trust_engine.all_profiles()
    active_agents = len(all_profiles)
    avg_trust = (
        sum(p.trust_score for p in all_profiles) / active_agents
        if active_agents > 0
        else 0.0
    )

    # ── Session metrics ───────────────────────────────────────────────────────
    all_sessions = replay_engine.list_sessions(limit=_MAX_SESSIONS_SCAN)
    total_sessions = len(all_sessions)

    threat_sessions = sum(
        1 for s in all_sessions
        if s.peak_risk_score is not None and s.peak_risk_score > 0.0
    )
    blocked_sessions = sum(
        1 for s in all_sessions
        if s.final_decision == "BLOCK"
    )

    # ── Recent decisions (last 10 completed sessions) ─────────────────────────
    completed = [s for s in all_sessions if s.status == SessionStatus.COMPLETE]
    # Already sorted newest-first by list_sessions().
    recent: list[RecentDecisionItem] = []
    for s in completed[:10]:
        if s.final_decision:
            recent.append(
                RecentDecisionItem(
                    session_id=s.session_id,
                    agent_id=s.agent_id,
                    decision=s.final_decision,
                    risk_score=s.peak_risk_score,
                    started_at=s.started_at,
                )
            )

    return DashboardResponse(
        active_agents=active_agents,
        total_sessions=total_sessions,
        threat_sessions=threat_sessions,
        blocked_sessions=blocked_sessions,
        average_trust_score=round(avg_trust, 4),
        recent_decisions=recent,
    )


# ── Internal constant — max sessions scanned for aggregation ──────────────────
_MAX_SESSIONS_SCAN: int = 1000
