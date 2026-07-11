"""Dependency injection providers for AgentShield X API.

All security engines and the replay subsystem are instantiated **once** at
module import time and surfaced to routers via FastAPI dependency functions.
This keeps every router stateless and makes unit-testing trivial — swap a
provider and all routes that depend on it are automatically updated.

Engine singletons
-----------------
Each engine is a single module-level instance.  They are all thread-safe
(they manage their own ``RLock``).  No additional synchronisation is needed
in the routers.

Usage in a router::

    from fastapi import Depends
    from app.api.deps import get_detection_engine, get_trust_engine

    @router.post("/analyze")
    def analyze(
        detection_engine: DetectionEngine = Depends(get_detection_engine),
        trust_engine: TrustEngine        = Depends(get_trust_engine),
    ):
        ...

Future extension points
-----------------------
TODO [AUTH]:       Add ``get_current_user`` dependency backed by JWT decode.
TODO [RBAC]:       Add ``require_role("analyst")`` dependency factory.
TODO [RATE_LIMIT]: Add ``rate_limited`` dependency (token-bucket per IP).
TODO [DB]:         Add ``get_db_session`` for SQLAlchemy async session.
"""

from __future__ import annotations

from app.core.behavior_dna import BehaviorDNAEngine
from app.core.decision_engine import DecisionEngine
from app.core.detector import DetectionEngine
from app.core.replay import ReplayEngine, TimelineBuilder
from app.core.trust_engine import TrustEngine

# ── Engine singletons (created once, shared across all requests) ──────────────
_detection_engine = DetectionEngine()
_trust_engine = TrustEngine()
_decision_engine = DecisionEngine()
_dna_engine = BehaviorDNAEngine()
_replay_engine = ReplayEngine()
_timeline_builder = TimelineBuilder()


# ── Provider functions (called by FastAPI DI) ─────────────────────────────────


def get_detection_engine() -> DetectionEngine:
    """Return the shared :class:`~app.core.detector.DetectionEngine` instance.

    Returns:
        DetectionEngine: The module-level singleton.
    """
    return _detection_engine


def get_trust_engine() -> TrustEngine:
    """Return the shared :class:`~app.core.trust_engine.TrustEngine` instance.

    Returns:
        TrustEngine: The module-level singleton.
    """
    return _trust_engine


def get_decision_engine() -> DecisionEngine:
    """Return the shared :class:`~app.core.decision_engine.DecisionEngine` instance.

    Returns:
        DecisionEngine: The module-level singleton.
    """
    return _decision_engine


def get_dna_engine() -> BehaviorDNAEngine:
    """Return the shared :class:`~app.core.behavior_dna.BehaviorDNAEngine` instance.

    Returns:
        BehaviorDNAEngine: The module-level singleton.
    """
    return _dna_engine


def get_replay_engine() -> ReplayEngine:
    """Return the shared :class:`~app.core.replay.ReplayEngine` instance.

    Returns:
        ReplayEngine: The module-level singleton.
    """
    return _replay_engine


def get_timeline_builder() -> TimelineBuilder:
    """Return the shared :class:`~app.core.replay.TimelineBuilder` instance.

    The builder is stateless; it is safe to share across threads without
    any additional locking.

    Returns:
        TimelineBuilder: The module-level singleton.
    """
    return _timeline_builder
