"""Health check router for AgentShield API v1.

Endpoint
--------
``GET /api/v1/health``

Returns a lightweight liveness/readiness response that confirms:

* The API is reachable.
* All engine singletons were initialised without errors.
* How long the process has been running.

This is intentionally the *simplest* router — it has no dependencies on
external services, databases, or engines and should always return ``200 OK``
as long as the Python process is alive.

Future extension points
-----------------------
TODO [READINESS]:   Add a ``/health/ready`` endpoint that checks upstream
                    dependencies (DB, Redis, etc.) and returns ``503`` when
                    not ready.
TODO [LIVENESS]:    Separate liveness (``/health/live``) from readiness so
                    container orchestrators can distinguish the two.
TODO [METRICS]:     Expose a ``/metrics`` endpoint compatible with Prometheus
                    scraping.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends

from app.api.deps import (
    get_decision_engine,
    get_detection_engine,
    get_dna_engine,
    get_replay_engine,
    get_trust_engine,
)
from app.api.schemas import HealthResponse
from app.core.behavior_dna import BehaviorDNAEngine
from app.core.decision_engine import DecisionEngine
from app.core.detector import DetectionEngine
from app.core.replay import ReplayEngine
from app.core.trust_engine import TrustEngine

# ── Module-level start time (seconds since epoch) ────────────────────────────
_START_TIME: float = time.monotonic()

# ── API version surfaced in the health response ───────────────────────────────
_API_VERSION = "1.0.0"

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    response_model=HealthResponse,
    summary="API Health Check",
    description=(
        "Returns the current health status of the API and all engine "
        "singletons. Always ``200 OK`` while the process is running."
    ),
)
def health_check(
    detection_engine: DetectionEngine = Depends(get_detection_engine),
    trust_engine: TrustEngine = Depends(get_trust_engine),
    decision_engine: DecisionEngine = Depends(get_decision_engine),
    dna_engine: BehaviorDNAEngine = Depends(get_dna_engine),
    replay_engine: ReplayEngine = Depends(get_replay_engine),
) -> HealthResponse:
    """Return the API health status and engine readiness.

    Args:
        detection_engine: Injected ``DetectionEngine`` singleton.
        trust_engine: Injected ``TrustEngine`` singleton.
        decision_engine: Injected ``DecisionEngine`` singleton.
        dna_engine: Injected ``BehaviorDNAEngine`` singleton.
        replay_engine: Injected ``ReplayEngine`` singleton.

    Returns:
        :class:`~app.api.schemas.HealthResponse` with status, version, uptime,
        and per-engine readiness flags.
    """
    uptime = time.monotonic() - _START_TIME

    engines: dict[str, str] = {
        "DetectionEngine": "ready" if detection_engine is not None else "error",
        "TrustEngine": "ready" if trust_engine is not None else "error",
        "DecisionEngine": "ready" if decision_engine is not None else "error",
        "BehaviorDNAEngine": "ready" if dna_engine is not None else "error",
        "ReplayEngine": "ready" if replay_engine is not None else "error",
    }

    return HealthResponse(
        status="ok",
        version=_API_VERSION,
        uptime_seconds=round(uptime, 3),
        engines=engines,
    )
