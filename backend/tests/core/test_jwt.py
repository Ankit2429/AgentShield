import pytest
import time
from app.utils.jwt import create_token, verify_token, revoked_tokens

SECRET_KEY = "test_secret_key"

def test_create_and_verify_access_token():
    token = create_token("admin@example.com", "Admin", SECRET_KEY, "access", 900)
    assert token is not None
    payload = verify_token(token, SECRET_KEY, "access")
    assert payload["sub"] == "admin@example.com"
    assert payload["role"] == "Admin"
    assert payload["type"] == "access"

def test_create_and_verify_refresh_token():
    token = create_token("analyst@example.com", "Security Analyst", SECRET_KEY, "refresh", 604800)
    payload = verify_token(token, SECRET_KEY, "refresh")
    assert payload["type"] == "refresh"

def test_verify_token_invalid_signature():
    token = create_token("user@example.com", "Viewer", SECRET_KEY, "access", 900)
    with pytest.raises(ValueError, match="Token signature verification failed."):
        verify_token(token, "wrong_secret_key", "access")

def test_verify_token_expired():
    token = create_token("user@example.com", "Viewer", SECRET_KEY, "access", -10)
    with pytest.raises(ValueError, match="Token has expired."):
        verify_token(token, SECRET_KEY, "access")

def test_verify_token_wrong_type():
    token = create_token("user@example.com", "Viewer", SECRET_KEY, "access", 900)
    with pytest.raises(ValueError, match="Invalid token type."):
        verify_token(token, SECRET_KEY, "refresh")

def test_token_revocation():
    token = create_token("user@example.com", "Viewer", SECRET_KEY, "refresh", 900)
    payload = verify_token(token, SECRET_KEY, "refresh")
    jti = payload["jti"]
    
    revoked_tokens.revoke(jti)
    assert revoked_tokens.is_revoked(jti) is True
    
    with pytest.raises(ValueError, match="Token has been revoked."):
        verify_token(token, SECRET_KEY, "refresh")
