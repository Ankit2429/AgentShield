"""AgentShield API v1 routers package.

All routers are imported here and re-exported for registration in
:mod:`app.api`.  Adding a new router only requires adding it to this module
and registering it in :mod:`app.api`.
"""

from app.api.routers.agents import router as agents_router
from app.api.routers.analyze import router as analyze_router
from app.api.routers.auth import router as auth_router
from app.api.routers.dashboard import router as dashboard_router
from app.api.routers.health import router as health_router
from app.api.routers.replay import router as replay_router
from app.api.routers.ws import router as ws_router

__all__ = [
    "analyze_router",
    "auth_router",
    "replay_router",
    "agents_router",
    "dashboard_router",
    "health_router",
    "ws_router",
]
