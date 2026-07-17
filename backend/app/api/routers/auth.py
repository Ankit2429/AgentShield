"""Authentication and Authorization Router for AgentShield.

Manages security credentials, issues JWT access/refresh token pairs, handles
refresh token rotation, and invalidates active sessions upon logout.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import sys
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.api.schemas import AuthLoginRequest, AuthRefreshRequest, TokenResponse, UserMeResponse
from app.config import settings
from app.utils.jwt import create_token, revoked_tokens, verify_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# ---------------------------------------------------------------------------
# User credential store
# ---------------------------------------------------------------------------
# In non-demo production the dict stays empty; a real backing database would
# be wired in here via [STORAGE] extension point.
#
# Seeding rules:
#   APP_ENV != production  → always seed (local dev / CI)
#   APP_ENV == production
#     DEMO_MODE=true       → seed  (hackathon / hosted demo)
#     DEMO_MODE=false      → skip  (real production with a proper user DB)
# ---------------------------------------------------------------------------
USER_DB: dict[str, dict[str, Any]] = {}

_should_seed = (settings.APP_ENV != "production") or settings.DEMO_MODE

if _should_seed:
    _mode_label = "Development/Demo" if settings.APP_ENV != "production" else "Production+DEMO_MODE"
    sys.stderr.write(f"[AUTH] {_mode_label}: seeding demo user accounts (APP_ENV={settings.APP_ENV}, DEMO_MODE={settings.DEMO_MODE}).\n")
    sys.stderr.flush()
    _DEMO_CREDENTIALS = {
        "admin@agentshield.com":    {"password": "admin-password",    "role": "Admin"},
        "analyst@agentshield.com":  {"password": "analyst-password",  "role": "Security Analyst"},
        "viewer@agentshield.com":   {"password": "viewer-password",   "role": "Viewer"},
    }
    for email, data in _DEMO_CREDENTIALS.items():
        salt = os.urandom(16)
        key = hashlib.pbkdf2_hmac("sha256", data["password"].encode("utf-8"), salt, 100000)
        USER_DB[email] = {"salt": salt, "key": key, "role": data["role"]}
    _DEMO_CREDENTIALS.clear()  # Wipe plain-text passwords from memory immediately
    sys.stderr.write(f"[AUTH] Demo accounts seeded: {list(USER_DB.keys())}\n")
    sys.stderr.write(f"[AUTH] Demo users seeded: YES  (count={len(USER_DB)})\n")
    sys.stderr.flush()
else:
    sys.stderr.write(
        f"[AUTH] APP_ENV={settings.APP_ENV} | DEMO_MODE={settings.DEMO_MODE}\n"
        f"[AUTH] Demo users seeded: NO\n"
        f"[AUTH] USER_DB is EMPTY — login will fail for all accounts.\n"
        f"[AUTH] ACTION REQUIRED: set DEMO_MODE=true in Render environment variables.\n"
    )
    sys.stderr.flush()


def verify_password(plain_password: str, salt: bytes, hashed_key: bytes) -> bool:
    """Validate plain credentials using constant-time PBKDF2 comparison."""
    new_key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 100000)
    return hmac.compare_digest(new_key, hashed_key)


from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

@router.post("/login", response_model=TokenResponse)
async def login(payload: OAuth2PasswordRequestForm = Depends()) -> dict[str, Any]:
    """Authenticate credentials and return a secure access/refresh token pair."""
    email = payload.username.lower().strip()
    user = USER_DB.get(email)

    print(f"[AUTH] Login attempt: username={email!r}", flush=True)
    if not user:
        print(f"[AUTH] User NOT found in USER_DB: {email!r}. Stored keys: {list(USER_DB.keys())}", flush=True)
    else:
        pw_ok = verify_password(payload.password, user["salt"], user["key"])
        print(f"[AUTH] User found. Password correct: {pw_ok}", flush=True)

    if not user or not verify_password(payload.password, user["salt"], user["key"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed. Invalid email address or password credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_token(
        subject=email,
        role=user["role"],
        secret_key=settings.SECRET_KEY,
        token_type="access",
        expires_in=900,  # 15 mins
    )

    refresh_token = create_token(
        subject=email,
        role=user["role"],
        secret_key=settings.SECRET_KEY,
        token_type="refresh",
        expires_in=604800,  # 7 days
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 900,
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: AuthRefreshRequest) -> dict[str, Any]:
    """Enforce refresh token rotation.

    Validates the refresh token, revokes it immediately to prevent reuse, and
    issues a new pair of access and refresh tokens.
    """
    try:
        claims = verify_token(
            token=payload.refresh_token,
            secret_key=settings.SECRET_KEY,
            expected_type="refresh",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed. {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    email = claims["sub"]
    role = claims["role"]
    jti = claims.get("jti")

    if jti:
        revoked_tokens.revoke(jti)  # Revoke to implement Token Rotation (prevent reuse)

    access_token = create_token(
        subject=email,
        role=role,
        secret_key=settings.SECRET_KEY,
        token_type="access",
        expires_in=900,
    )

    refresh_token = create_token(
        subject=email,
        role=role,
        secret_key=settings.SECRET_KEY,
        token_type="refresh",
        expires_in=604800,
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 900,
    }


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: AuthRefreshRequest) -> None:
    """Revoke the active refresh token upon logging out."""
    try:
        claims = verify_token(
            token=payload.refresh_token,
            secret_key=settings.SECRET_KEY,
            expected_type="refresh",
        )
        jti = claims.get("jti")
        if jti:
            revoked_tokens.revoke(jti)
    except ValueError:
        # Silently succeed on logout of invalid token to prevent user enumeration
        pass
    return


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    """Dependency validator verifying JWT token and returning user context."""
    try:
        claims = verify_token(token=token, secret_key=settings.SECRET_KEY, expected_type="access")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Access token validation failed: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return {"email": claims["sub"], "role": claims["role"]}


def require_roles(*allowed_roles: str) -> Any:
    """Enforce Role-Based Access Control (RBAC) constraint checks on endpoints."""

    async def rbac_dependency(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        role = current_user.get("role")
        if role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role permissions: {allowed_roles}. Current role: {role}.",
            )
        return current_user

    return rbac_dependency


@router.get("/me", response_model=UserMeResponse)
async def get_me(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """Retrieve details of the currently authenticated caller context."""
    return {
        "email": current_user["email"],
        "role": current_user["role"],
    }
