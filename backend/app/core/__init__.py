# AgentShield Core Security and Trust Engine Package
"""Public API for all AgentShield core engines and the event bus.

Usage::

    # Engines
    from app.core import DetectionEngine, DetectionResult, Severity
    from app.core import TrustEngine, AgentTrustProfile, TrustStatus, TrustTrend
    from app.core import DecisionEngine, DecisionResult, Decision, DecisionSeverity
    from app.core import ReasonCode, Recommendation
    from app.core import BehaviorDNAEngine, BehaviorObservation, BehaviorProfile
    from app.core import BehaviorAnalysis, DeviationLevel

    # Event bus
    from app.core import SecurityEvent, make_event, enrich, obs_from_event
    from app.core import EventStage, event_stage, to_audit_dict

    # Attack Replay Engine
    from app.core import ReplayEngine, TimelineBuilder, ReplaySession
    from app.core import ReplayFrame, ReplayStage, SessionStatus
    from app.core import session_to_json, session_from_json
"""


# ── Engines ───────────────────────────────────────────────────────────────────
from app.core.behavior_dna import (
    BehaviorAnalysis,
    BehaviorDNAEngine,
    BehaviorObservation,
    BehaviorProfile,
    DeviationLevel,
)
from app.core.decision_engine import (
    Decision,
    DecisionEngine,
    DecisionResult,
    DecisionSeverity,
    ReasonCode,
    Recommendation,
)
from app.core.detector import DetectionEngine
from app.core.models import DetectionResult, ThreatResult, ThreatRule
from app.core.severity import Severity
from app.core.trust_engine import (
    AgentTrustProfile,
    TrustEngine,
    TrustStatus,
    TrustTrend,
)

# ── Event bus ─────────────────────────────────────────────────────────────────
from app.core.events import (
    EventStage,
    SecurityEvent,
    assert_stage_at_least,
    enrich,
    event_decision_value,
    event_risk_score,
    event_stage,
    is_actionable,
    make_event,
    obs_from_event,
    to_audit_dict,
)

# ── Attack Replay Engine ───────────────────────────────────────────────────────────
from app.core.replay import (
    ReplayEngine,
    ReplayFrame,
    ReplaySession,
    ReplayStage,
    SessionStatus,
    TimelineBuilder,
    frame_from_dict,
    frame_to_dict,
    make_frame,
    make_session,
    session_from_dict,
    session_from_json,
    session_to_dict,
    session_to_json,
)

__all__ = [
    # ── Detection Engine ──────────────────────────────────────────────────────
    "DetectionEngine",
    "DetectionResult",
    "ThreatResult",
    "ThreatRule",
    "Severity",
    # ── Trust Engine ──────────────────────────────────────────────────────────
    "TrustEngine",
    "AgentTrustProfile",
    "TrustStatus",
    "TrustTrend",
    # ── Decision Engine ───────────────────────────────────────────────────────
    "DecisionEngine",
    "DecisionResult",
    "Decision",
    "DecisionSeverity",
    "ReasonCode",
    "Recommendation",
    # ── Behavioral DNA Engine ─────────────────────────────────────────────────
    "BehaviorDNAEngine",
    "BehaviorObservation",
    "BehaviorProfile",
    "BehaviorAnalysis",
    "DeviationLevel",
    # ── Event Bus ─────────────────────────────────────────────────────────────
    "SecurityEvent",
    "make_event",
    "enrich",
    "obs_from_event",
    "EventStage",
    "event_stage",
    "assert_stage_at_least",
    "is_actionable",
    "event_risk_score",
    "event_decision_value",
    "to_audit_dict",
    # ── Attack Replay Engine ───────────────────────────────────────────────────────────
    "ReplayEngine",
    "TimelineBuilder",
    "ReplayFrame",
    "ReplaySession",
    "ReplayStage",
    "SessionStatus",
    "make_frame",
    "make_session",
    "session_to_json",
    "session_from_json",
    "session_to_dict",
    "session_from_dict",
    "frame_to_dict",
    "frame_from_dict",
]
