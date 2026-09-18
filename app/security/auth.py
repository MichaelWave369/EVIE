from __future__ import annotations
from fastapi import Header, HTTPException
from app.settings import settings

def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    # simple local-only guard: you can disable by setting EV_API_KEY to empty and passing empty header
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
