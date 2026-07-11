"""Pydantic request and response schemas for the AgentShield X API v1.

All models in this module are the **only** types that cross the HTTP boundary.
Existing engine dataclasses are never exposed directly — they are always
translated here.  This keeps the API contract stable regardless of internal
refactors.

Naming convention
-----------------
* ``*Request``  – inbound request bodies (POST / PUT).
* ``*Response`` – outbound response bodies (GET / POST).
* ``*Item``     – nested objects embedded inside responses.

Future extension points
-----------------------
TODO [PAGINATION]: Add ``PaginatedResponse[T]`` generic wrapper with
                   ``total``, ``page``, ``page_size``, ``items`` fields.
TODO [AUTH]:       Add ``TokenResponse`` and ``UserContext`` models for JWT.
TODO [WEBSOCKET]:  Add ``EventStreamMessage`` for SSE / WebSocket streaming.
TODO [VERSIONING]: Add ``ApiError`` with a ``code`` field for machine-readable
                   error codes (e.g. ``ERR_AGENT_BLOCKED``).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import re
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Shared atoms
# ============================================================================


class ThreatItem(BaseModel):
    """A single matched threat rule.

    Attributes:
        name: Human-readable rule name.
        category: Broad threat category (e.g. ``"command_injection"``).
        severity: Severity level string (e.g. ``"CRITICAL"``).
        matched_text: The exact substring that triggered the rule.
    """

    name: str
    category: str
    severity: str
    matched_text: str


class FrameItem(BaseModel):
    """One stage in a replay timeline.

    Attributes:
        frame_id: Unique frame identifier.
        stage: Canonical stage name (e.g. ``"DETECTED"``).
        timestamp: UTC timestamp when the frame was recorded.
        title: Short human-readable stage label.
        description: One-sentence explanation of what happened.
        engine: Name of the engine that produced this frame.
        risk_score: Risk score at this stage (may be ``None``).
        trust_score: Trust score at this stage (may be ``None``).
        decision: Decision value at this stage (may be ``None``).
        metadata: Engine-specific detail dict.
    """

    frame_id: str
    stage: str
    timestamp: datetime
    title: str
    description: str
    engine: str
    risk_score: Optional[float] = None
    trust_score: Optional[float] = None
    decision: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# POST /api/v1/analyze
# ============================================================================


class AnalyzeRequest(BaseModel):
    """Request body for ``POST /api/v1/analyze``.

    Attributes:
        agent_id: Stable identifier of the requesting AI agent.
        message: Raw text message submitted by the agent.
        requested_tool: Optional capability name the agent is requesting.
        metadata: Arbitrary caller-supplied context (session, region, etc.).

    Example::

        {
          "agent_id": "agent-42",
          "message": "list /etc/passwd",
          "requested_tool": "file_read",
          "metadata": {"session_id": "s-001"}
        }
    """
    model_config = {
        "extra": "forbid"
    }

    agent_id: str = Field(..., min_length=1, max_length=256, description="Stable agent identifier.")
    message: str = Field(..., min_length=1, max_length=32_768, description="Raw agent message.")
    requested_tool: Optional[str] = Field(None, max_length=128, description="Optional tool name.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Caller-supplied context.")

    @field_validator("agent_id", "message")
    @classmethod
    def _strip_whitespace(cls, v: str) -> str:
        """Strip leading / trailing whitespace from string fields."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Field must not be blank.")
        return stripped


class DetectionSummary(BaseModel):
    """Detection Engine output summary embedded in :class:`AnalyzeResponse`.

    Attributes:
        is_malicious: ``True`` when at least one threat pattern matched.
        risk_score: Aggregate risk in ``[0.0, 1.0]``.
        threat_count: Total number of matched rules.
        threats: Individual threat matches (up to 10).
    """

    is_malicious: bool
    risk_score: float
    threat_count: int
    threats: list[ThreatItem] = Field(default_factory=list)


class BehaviorSummary(BaseModel):
    """Behavioral DNA output embedded in :class:`AnalyzeResponse`.

    Attributes:
        behavior_similarity: Similarity to the agent's baseline ``[0, 1]``.
        behavior_deviation: Deviation from baseline ``[0, 1]``.
        deviation_level: Human-readable level (e.g. ``"HIGH"``).
        reasons: Up to 10 human-readable anomaly signals.
        summary: One-sentence summary from the DNA engine.
    """

    behavior_similarity: float
    behavior_deviation: float
    deviation_level: str
    reasons: list[str] = Field(default_factory=list)
    summary: str


class TrustSummary(BaseModel):
    """Trust Engine output embedded in :class:`AnalyzeResponse`.

    Attributes:
        trust_score: Overall trust score in ``[0.0, 1.0]``.
        behavior_score: Behavioural component score.
        policy_score: Policy compliance component score.
        security_grade: Letter grade (e.g. ``"A+"``).
        status: Agent lifecycle status (e.g. ``"VERIFIED"``).
        trend: Score direction (``"IMPROVING"`` / ``"STABLE"`` / ``"DECLINING"``).
    """

    trust_score: float
    behavior_score: float
    policy_score: float
    security_grade: str
    status: str
    trend: str


class DecisionSummary(BaseModel):
    """Decision Engine output embedded in :class:`AnalyzeResponse`.

    Attributes:
        decision: Verdict (``"ALLOW"`` / ``"MONITOR"`` / ``"REVIEW"`` /
            ``"QUARANTINE"`` / ``"BLOCK"``).
        confidence: Confidence in ``[0.0, 1.0]``.
        severity: Decision severity level string.
        recommendation: Recommended action string.
        reason_codes: Machine-readable reason codes.
        explanation: Human-readable explanation paragraph.
    """

    decision: str
    confidence: float
    severity: str
    recommendation: str
    reason_codes: list[str] = Field(default_factory=list)
    explanation: str


class AnalyzeResponse(BaseModel):
    """Response body for ``POST /api/v1/analyze``.

    Attributes:
        event_id: Unique ID of the processed :class:`~app.core.events.schema.SecurityEvent`.
        agent_id: Agent that submitted the request.
        session_id: ID of the replay session created for this event.
        timestamp: UTC time the event was processed.
        stage: Final enrichment stage reached.
        detection: Detection Engine output.
        behavior: Behavioral DNA output (``None`` if insufficient baseline).
        trust: Trust Engine output.
        decision: Decision Engine verdict.
    """

    event_id: str
    agent_id: str
    session_id: str
    timestamp: datetime
    stage: str
    detection: DetectionSummary
    behavior: Optional[BehaviorSummary] = None
    trust: TrustSummary
    decision: DecisionSummary


# ============================================================================
# GET /api/v1/replay/{session_id}  &  GET /api/v1/replay
# ============================================================================


class ReplaySessionResponse(BaseModel):
    """Full replay session response for ``GET /api/v1/replay/{session_id}``.

    Attributes:
        session_id: Unique session identifier.
        event_id: Originating event ID.
        agent_id: Agent that generated the event.
        status: Session lifecycle status.
        started_at: UTC session creation time.
        completed_at: UTC session completion time (``None`` if still open).
        overall_summary: Human-readable session verdict.
        frame_count: Number of frames in the timeline.
        duration_ms: Session duration in milliseconds.
        final_decision: Decision from the last ``DECISION_MADE`` frame.
        peak_risk_score: Maximum risk score across all frames.
        stages_completed: Ordered list of stage names completed.
        frames: Full ordered list of :class:`FrameItem` objects.
    """

    session_id: str
    event_id: str
    agent_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    overall_summary: str
    frame_count: int
    duration_ms: Optional[float] = None
    final_decision: Optional[str] = None
    peak_risk_score: Optional[float] = None
    stages_completed: list[str] = Field(default_factory=list)
    frames: list[FrameItem] = Field(default_factory=list)


class ReplaySessionSummary(BaseModel):
    """Lightweight session summary for ``GET /api/v1/replay`` list endpoint.

    Attributes:
        session_id: Unique session identifier.
        event_id: Originating event ID.
        agent_id: Agent identifier.
        status: Session lifecycle status.
        started_at: UTC session creation time.
        frame_count: Number of frames.
        final_decision: Decision outcome (``None`` if not yet decided).
        peak_risk_score: Highest risk score observed.
    """

    session_id: str
    event_id: str
    agent_id: str
    status: str
    started_at: datetime
    frame_count: int
    final_decision: Optional[str] = None
    peak_risk_score: Optional[float] = None


class ReplayListResponse(BaseModel):
    """Response body for ``GET /api/v1/replay``.

    Attributes:
        total: Total number of sessions returned (after filtering).
        sessions: List of lightweight session summaries.
    """

    total: int
    sessions: list[ReplaySessionSummary] = Field(default_factory=list)


# ============================================================================
# GET /api/v1/agents
# ============================================================================


class AgentProfileResponse(BaseModel):
    """Agent trust profile returned by ``GET /api/v1/agents``.

    Attributes:
        agent_id: Stable agent identifier.
        trust_score: Current composite trust score.
        behavior_score: Behavioural component score.
        policy_score: Policy compliance component score.
        security_grade: Letter grade.
        status: Lifecycle status string.
        trend: Score direction.
        successful_requests: Lifetime count of successful requests.
        blocked_requests: Lifetime count of blocked requests.
        suspicious_requests: Lifetime count of suspicious requests.
        last_updated: UTC timestamp of the most recent profile update.
    """

    agent_id: str
    trust_score: float
    behavior_score: float
    policy_score: float
    security_grade: str
    status: str
    trend: str
    successful_requests: int
    blocked_requests: int
    suspicious_requests: int
    last_updated: datetime


class AgentListResponse(BaseModel):
    """Response body for ``GET /api/v1/agents``.

    Attributes:
        total: Total number of agent profiles returned.
        agents: List of agent trust profiles.
    """

    total: int
    agents: list[AgentProfileResponse] = Field(default_factory=list)


# ============================================================================
# GET /api/v1/dashboard
# ============================================================================


class RecentDecisionItem(BaseModel):
    """One entry in the recent-decisions list on the dashboard.

    Attributes:
        session_id: Replay session ID.
        agent_id: Agent involved.
        decision: Final verdict string.
        risk_score: Peak risk score from the session.
        started_at: UTC timestamp of the analysis.
    """

    session_id: str
    agent_id: str
    decision: str
    risk_score: Optional[float] = None
    started_at: datetime


class DashboardResponse(BaseModel):
    """Response body for ``GET /api/v1/dashboard``.

    Attributes:
        active_agents: Number of unique agents with at least one profile.
        total_sessions: Total replay sessions in memory.
        threat_sessions: Sessions where a threat was detected (risk > 0).
        blocked_sessions: Sessions that ended in a ``BLOCK`` decision.
        average_trust_score: Mean trust score across all known agents.
        recent_decisions: Up to 10 most recent completed session decisions.
    """

    active_agents: int
    total_sessions: int
    threat_sessions: int
    blocked_sessions: int
    average_trust_score: float
    recent_decisions: list[RecentDecisionItem] = Field(default_factory=list)


# ============================================================================
# GET /api/v1/health
# ============================================================================


class HealthResponse(BaseModel):
    """Response body for ``GET /api/v1/health``.

    Attributes:
        status: Always ``"ok"`` when the API is reachable.
        version: API version string.
        uptime_seconds: Seconds since the FastAPI application started.
        engines: Dict of engine names → ``"ready"`` confirming each engine
            singleton was initialised successfully.
    """

    status: str
    version: str
    uptime_seconds: float
    engines: dict[str, str] = Field(default_factory=dict)


# ============================================================================
# Authentication Schemas
# ============================================================================

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class AuthLoginRequest(BaseModel):
    """Request payload for logging in to the platform."""
    model_config = {
        "extra": "forbid"
    }

    email: str = Field(..., min_length=5, max_length=256, description="User email address.")
    password: str = Field(..., min_length=8, max_length=128, description="User credential password.")

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        stripped = v.strip().lower()
        if not EMAIL_REGEX.match(stripped):
            raise ValueError("Invalid email address format.")
        return stripped


class AuthRefreshRequest(BaseModel):
    """Request payload for renewing access tokens."""
    model_config = {
        "extra": "forbid"
    }

    refresh_token: str = Field(..., description="Active Refresh JWT token.")


class TokenResponse(BaseModel):
    """Outbound payload returning valid session credentials."""
    model_config = {
        "extra": "forbid"
    }

    access_token: str = Field(..., description="Access token JWT.")
    refresh_token: str = Field(..., description="Rotated refresh token JWT.")
    token_type: str = Field("bearer", description="Token authentication schema scheme.")
    expires_in: int = Field(900, description="Access token validity lifespan in seconds.")


class UserMeResponse(BaseModel):
    """Authenticated caller identification details."""
    model_config = {
        "extra": "forbid"
    }

    email: str = Field(..., description="User identifier.")
    role: str = Field(..., description="Assigned authorization role (Admin, Analyst, Viewer).")

