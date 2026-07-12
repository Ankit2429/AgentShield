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

import os
import time
import traceback

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

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

# ── Custom Middlewares ────────────────────────────────────────────────────────

class HardeningHeadersMiddleware(BaseHTTPMiddleware):
    """Inject browser security hardening headers into all responses."""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Bypass hardening headers for documentation endpoints
        if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            return response
            
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store, max-age=0"
        
        # CSP: Safe directives allowing local self, WebSockets, and scripts
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "connect-src 'self' ws: wss: http: https:;"
        )
        return response


class RequestSizeLimiterMiddleware(BaseHTTPMiddleware):
    """Enforce request size limits (max 2MB) to prevent buffer overflows."""
    def __init__(self, app, max_upload_size: int = 2 * 1024 * 1024):
        super().__init__(app)
        self.max_upload_size = max_upload_size

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.max_upload_size:
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={"detail": "Payload too large. Maximum size allowed is 2MB."}
                    )
            except ValueError:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid Content-Length header."}
                )
        return await call_next(request)


app.add_middleware(HardeningHeadersMiddleware)
app.add_middleware(RequestSizeLimiterMiddleware)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Restrict origins in production environment
cors_allowed_origins = ["*"]
allow_creds = False
if settings.APP_ENV == "production":
    raw_origins = os.getenv("CORS_ORIGIN_WHITELIST", "https://agentshield.vercel.app")
    if raw_origins.strip() == "*":
        cors_allowed_origins = ["*"]
        allow_creds = False
    else:
        cors_allowed_origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
        if "https://agentshield.vercel.app" not in cors_allowed_origins:
            cors_allowed_origins.append("https://agentshield.vercel.app")
        allow_creds = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed_origins,
    allow_credentials=allow_creds,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception Handlers ────────────────────────────────────────────────────────
import logging
logger = logging.getLogger("agentshield.api")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Centralized validation error handler that suppresses raw framework output."""
    logger.warning(f"[SECURITY WARNING] Validation failed on path {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Request validation failed. Malformed inputs or unexpected fields detected."}
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Standard HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Fallback handler that suppresses internal tracebacks in production."""
    # Write structured audit/error log to stderr
    print(f"[CRITICAL ERROR] Unhandled request error on path {request.url.path}: {exc}")
    traceback.print_exc()
    
    detail = "An internal server error occurred."
    if settings.APP_ENV == "development":
        detail = f"Unhandled Exception: {exc}"
        
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": detail}
    )

# ── API v1 ────────────────────────────────────────────────────────────────────
app.include_router(v1_router)
