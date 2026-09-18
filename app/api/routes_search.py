from __future__ import annotations
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.security.auth import require_api_key
from app.rag.retriever import retrieve
from app.search.fts import search as fts_search, rebuild as fts_rebuild

router = APIRouter(prefix="/v1/search", tags=["search"])

class SearchReq(BaseModel):
    query: str
    top_k: int = 8
    mode: str = "hybrid"  # vector | fts | hybrid
    fts_k: int = 10

@router.post("", dependencies=[Depends(require_api_key)])
def search(req: SearchReq):
    q = (req.query or "").strip()
    mode = (req.mode or "hybrid").lower()

    vec_hits = []
    if mode in ("vector", "hybrid"):
        vec_hits = retrieve(q, top_k=req.top_k)

    fts_hits = []
    if mode in ("fts", "hybrid"):
        try:
            fts_hits = fts_search(q, limit=req.fts_k)
        except Exception:
            fts_hits = []

    return {"query": q, "mode": mode, "hits": vec_hits, "fts_hits": fts_hits}


@router.post("/reindex", dependencies=[Depends(require_api_key)])
def reindex():
    """Rebuild the optional SQLite FTS index (best-effort)."""
    return fts_rebuild()
