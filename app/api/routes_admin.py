from __future__ import annotations
from fastapi import APIRouter, Depends
from app.security.auth import require_api_key
from app.db.schema import connect
import os

router = APIRouter(prefix="/v1/admin", tags=["admin"])

@router.get("/health", dependencies=[Depends(require_api_key)])
def health():
    return {"ok": True}

@router.get("/stats", dependencies=[Depends(require_api_key)])
def stats():
    con = connect()
    d = {}
    for table in ["sources","documents","chunks","vector_meta","products","assets","tasks","audit_log"]:
        try:
            r = con.execute(f"SELECT COUNT(*) as n FROM {table}").fetchone()
            d[table] = int(r["n"])
        except Exception:
            d[table] = None
    con.close()
    return d
