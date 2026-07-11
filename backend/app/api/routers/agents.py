"""Agents router for AgentShield X API v1.

Endpoint
--------
``GET /api/v1/agents``

Returns all agent trust profiles currently held in the
:class:`~app.core.trust_engine.TrustEngine`'s in-memory registry.

Each profile captures the long-term reputation of one AI agent: its composite
trust score, component scores, security grade, lifecycle status, and request
counters.

Future extension points
-----------------------
TODO [AUTH]:       Restrict to authenticated callers with the ``analyst`` role.
TODO [PAGINATION]: Add ``page`` / ``page_size`` query parameters.
TODO [SEARCH]:     Add a ``?q=`` full-text filter over ``agent_id``.
TODO [SORT]:       Add ``?sort=trust_score&order=asc`` sorting.
TODO [DELETE]:     Add ``DELETE /agents/{agent_id}`` for RBAC-gated agent
                   removal (quarantine purge workflow).
TODO [DETAIL]:     Add ``GET /agents/{agent_id}`` for a single-agent profile.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_trust_engine, require_roles
from app.api.schemas import AgentListResponse, AgentProfileResponse
from app.core.trust_engine import AgentTrustProfile, TrustEngine

router = APIRouter(prefix="/agents", tags=["Agents"])


# ============================================================================
# GET /agents
# ============================================================================


@router.get(
    "",
    response_model=AgentListResponse,
    summary="List Agent Trust Profiles",
    dependencies=[Depends(require_roles("Admin", "Security Analyst", "Viewer"))],
    description=(
        "Returns all AI agent trust profiles held in the Trust Engine, "
        "sorted by trust score descending."
    ),
)
def list_agents(
    min_trust: float = Query(0.0, ge=0.0, le=1.0, description="Minimum trust score filter."),
    max_trust: float = Query(1.0, ge=0.0, le=1.0, description="Maximum trust score filter."),
    agent_status: str = Query("", description="Filter by status (e.g. BLOCKED). Empty = all."),
    trust_engine: TrustEngine = Depends(get_trust_engine),
) -> AgentListResponse:
    """Return all known agent profiles from the Trust Engine.

    Args:
        min_trust: Only return agents with trust score ≥ this value.
        max_trust: Only return agents with trust score ≤ this value.
        agent_status: If non-empty, filter to profiles with this status.
        trust_engine: Injected :class:`~app.core.trust_engine.TrustEngine`.

    Returns:
        :class:`~app.api.schemas.AgentListResponse` sorted by trust score
        descending.
    """
    # TODO [AUTH]: Verify caller has at least the ``viewer`` role.

    profiles: list[AgentTrustProfile] = trust_engine.all_profiles()

    # Apply optional filters.
    if agent_status:
        profiles = [
            p for p in profiles
            if p.status.value.upper() == agent_status.upper()
        ]
    profiles = [
        p for p in profiles
        if min_trust <= p.trust_score <= max_trust
    ]

    # Sort highest trust first.
    profiles.sort(key=lambda p: p.trust_score, reverse=True)

    items = [_profile_to_response(p) for p in profiles]
    return AgentListResponse(total=len(items), agents=items)


# ============================================================================
# Private translation helper
# ============================================================================


def _profile_to_response(profile: AgentTrustProfile) -> AgentProfileResponse:
    """Translate an :class:`~app.core.trust_engine.AgentTrustProfile` to an
    :class:`~app.api.schemas.AgentProfileResponse`.

    Args:
        profile: Source trust profile.

    Returns:
        :class:`~app.api.schemas.AgentProfileResponse`.
    """
    return AgentProfileResponse(
        agent_id=profile.agent_id,
        trust_score=profile.trust_score,
        behavior_score=profile.behavior_score,
        policy_score=profile.policy_score,
        security_grade=profile.security_grade,
        status=profile.status.value,
        trend=profile.trend.value,
        successful_requests=profile.successful_requests,
        blocked_requests=profile.blocked_requests,
        suspicious_requests=profile.suspicious_requests,
        last_updated=profile.last_updated,
    )
