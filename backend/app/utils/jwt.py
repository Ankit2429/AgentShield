"""HS256 JWT signing and verification library for AgentShield X.

Custom implementation using standard libraries (hmac, hashlib, base64, json) to
eliminate external library dependency risk. Supports access/refresh token pairs
and revocation checks.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
import time
from typing import Any, Optional


class RevokedTokenRegistry:
    """Thread-safe registry for revoked JWT tokens (blacklist)."""

    def __init__(self) -> None:
        self._revoked_jtis: set[str] = set()
        self._lock = threading.Lock()

    def revoke(self, jti: str) -> None:
        """Add a token identifier to the blacklist."""
        if not jti:
            return
        with self._lock:
            self._revoked_jtis.add(jti)

    def is_revoked(self, jti: str) -> bool:
        """Check if a token identifier has been revoked."""
        if not jti:
            return False
        with self._lock:
            return jti in self._revoked_jtis


# Global revoked tokens registry
revoked_tokens = RevokedTokenRegistry()


def base64url_encode(data: bytes) -> str:
    """Encode bytes to a base64url string without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def base64url_decode(data: str) -> bytes:
    """Decode a base64url string with optional padding."""
    padding = "=" * (4 - (len(data) % 4))
    return base64.urlsafe_b64decode(data + padding)


def create_token(
    subject: str,
    role: str,
    secret_key: str,
    token_type: str = "access",
    expires_in: int = 900,  # Default 15 minutes
    jti: Optional[str] = None,
) -> str:
    """Generate a signed HS256 JWT token.

    Args:
        subject: The unique identifier of the subject (e.g. email).
        role: The role classification (Admin, Analyst, Viewer).
        secret_key: The HMAC signature key.
        token_type: The type category ('access' or 'refresh').
        expires_in: Lifespan seconds.
        jti: Optional token identifier.

    Returns:
        str: Three-part dot-separated JWT.
    """
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    
    payload = {
        "sub": subject,
        "role": role,
        "type": token_type,
        "iat": now,
        "exp": now + expires_in,
        "jti": jti or f"jwt-{now}-{hash(subject) & 0xffffffff:08x}"
    }

    header_b64 = base64url_encode(json.dumps(header).encode("utf-8"))
    payload_b64 = base64url_encode(json.dumps(payload).encode("utf-8"))

    msg = f"{header_b64}.{payload_b64}".encode("utf-8")
    sig = hmac.new(secret_key.encode("utf-8"), msg, hashlib.sha256).digest()
    sig_b64 = base64url_encode(sig)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def verify_token(token: str, secret_key: str, expected_type: str = "access") -> dict[str, Any]:
    """Validate and decode a JWT token.

    Args:
        token: Dot-separated JWT string.
        secret_key: Signing key.
        expected_type: Expected 'type' claim ('access' or 'refresh').

    Returns:
        dict: The decoded token payload claims.

    Raises:
        ValueError: If token signature, type, expiration, or format is invalid.
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format.")

    header_b64, payload_b64, sig_b64 = parts

    # 1. Verify Alg
    try:
        header = json.loads(base64url_decode(header_b64).decode("utf-8"))
        if header.get("alg") != "HS256":
            raise ValueError("Unsupported algorithm. Only HS256 is permitted.")
    except Exception as exc:
        raise ValueError("Malformed header.") from exc

    # 2. Verify Signature
    msg = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = hmac.new(secret_key.encode("utf-8"), msg, hashlib.sha256).digest()
    expected_sig_b64 = base64url_encode(expected_sig)

    if not hmac.compare_digest(sig_b64, expected_sig_b64):
        raise ValueError("Token signature verification failed.")

    # 3. Decode & Verify Claims
    try:
        payload = json.loads(base64url_decode(payload_b64).decode("utf-8"))
    except Exception as exc:
        raise ValueError("Malformed payload.") from exc

    jti = payload.get("jti")
    if jti and revoked_tokens.is_revoked(jti):
        raise ValueError("Token has been revoked.")

    if payload.get("type") != expected_type:
        raise ValueError(f"Invalid token type. Expected: {expected_type}")

    exp = payload.get("exp")
    if not exp or time.time() > exp:
        raise ValueError("Token has expired.")

    return payload
