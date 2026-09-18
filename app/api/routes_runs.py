from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query
from app.security.auth import require_api_key
from app.db import queries

router = APIRouter(prefix="/v1/runs", tags=["runs"])

@router.get("", dependencies=[Depends(require_api_key)])
def list_runs(status: str | None = Query(default=None), limit: int = Query(default=50, ge=1, le=500)):
    return {"runs": queries.list_runs(limit=int(limit), status=status)}

@router.get("/{run_id}", dependencies=[Depends(require_api_key)])
def get_run(run_id: int):
    try:
        return queries.get_run(int(run_id))
    except KeyError:
        raise HTTPException(status_code=404, detail="run_id not found")
