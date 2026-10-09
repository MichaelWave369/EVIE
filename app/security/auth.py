"""Fail-closed authentication for privileged local EVIE API endpoints."""
from __future__ import annotations
import hmac
from fastapi import Header, HTTPException
from app.settings import settings

UNSAFE_KEYS = frozenset({
    "", "change-me", "change-me-long-random", "my-secret-key-change-this",
    "replace-with-a-unique-random-secret", "changeme", "password", "secret",
})

def api_key_is_configured(value: str | None) -> bool:
    return isinstance(value, str) and value.strip() == value and value.lower() not in UNSAFE_KEYS

def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    secret = settings.api_key
    if not api_key_is_configured(secret):
        raise HTTPException(status_code=503, detail="EVIE API key is not configured securely")
    if not isinstance(x_api_key, str) or not hmac.compare_digest(x_api_key, secret):
        raise HTTPException(status_code=401, detail="Invalid API key")
