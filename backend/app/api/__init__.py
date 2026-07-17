"""AgentShield API package.

Provides the ``v1_router`` FastAPI ``APIRouter`` pre-configured with the
``/api/v1`` prefix and all sub-routers mounted.

Registration in :mod:`app.main`::

    from app.api import v1_router
    app.include_router(v1_router)
"""

from fastapi import APIRouter

from app.api.routers import (
    agents_router,
    analyze_router,
    auth_router,
    dashboard_router,
    health_router,
    replay_router,
    ws_router,
)

# Versioned parent router — all endpoints live under /api/v1
v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(auth_router)
v1_router.include_router(analyze_router)
v1_router.include_router(replay_router)
v1_router.include_router(agents_router)
v1_router.include_router(dashboard_router)
v1_router.include_router(health_router)
v1_router.include_router(ws_router)

__all__ = ["v1_router"]
