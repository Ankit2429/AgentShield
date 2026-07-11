"""AgentShield X — FastAPI application entry point.

The application mounts all API v1 routers under ``/api/v1``.
The legacy ``/health`` stub is replaced by the production health router.

Startup lifecycle
-----------------
Engine singletons are created at import time in :mod:`app.api.deps` and
remain alive for the lifetime of the process.  No special lifespan hooks are
needed unless persistent storage is added.

Future extension points
-----------------------
TODO [AUTH]:       Register JWT middleware (e.g. ``fastapi-jwt-auth``).
TODO [RBAC]:       Register a permission-enforcement middleware.
TODO [RATE_LIMIT]: Register ``slowapi`` or a custom token-bucket limiter.
TODO [SENTRY]:     Add ``sentry_sdk.init()`` for error tracking.
TODO [LIFESPAN]:   Add an ``asynccontextmanager`` lifespan to warm up heavy
                   resources (DB pool, ML models) before serving traffic.
"""

import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import v1_router
from app.config import settings

# ── Application instance ──────────────────────────────────────────────────────
app = FastAPI(
    title="AgentShield X — AI Security Intelligence Platform",
    description=(
        "Production-quality security intelligence platform for AI-to-AI "
        "communication.  Provides detection, trust, decision, and replay "
        "capabilities via a versioned REST API."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# TODO [AUTH]: Restrict allow_origins to the production frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API v1 ────────────────────────────────────────────────────────────────────
app.include_router(v1_router)
