
from __future__ import annotations
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from app.security.auth import require_api_key
from app.db import queries
from app.scheduler.task_worker import run_due

router = APIRouter(prefix="/v1/scheduler", tags=["scheduler"])

@router.get("/tasks", dependencies=[Depends(require_api_key)])
def tasks(status: Optional[str] = None, limit: int = 50):
    return {"ok": True, "rows": queries.list_tasks(status=status, limit=limit)}

class RunDueReq(BaseModel):
    max_tasks: int = 3

@router.post("/run_due", dependencies=[Depends(require_api_key)])
def run(req: RunDueReq):
    return run_due(max_tasks=req.max_tasks)
