
from __future__ import annotations
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.security.auth import require_api_key
from app.factory.factory import seed_queue, run_next, list_queue
from app.factory.catalog import export_catalog

router = APIRouter(prefix="/v1/factory", tags=["factory"])

class SeedReq(BaseModel):
    focus: str
    niches: Optional[List[str]] = None
    top_n: int = 9
    modules: Optional[List[str]] = None
    constraints_by_module: Dict[str, Dict[str, Any]] = {}
    priority: int = 0
    schedule_fib: bool = True

@router.post("/seed", dependencies=[Depends(require_api_key)])
def seed(req: SeedReq):
    return seed_queue(
        focus=req.focus,
        niches=req.niches,
        top_n=req.top_n,
        modules=req.modules,
        constraints_by_module=req.constraints_by_module,
        priority=req.priority,
        schedule_fib=req.schedule_fib,
    )

@router.get("/queue", dependencies=[Depends(require_api_key)])
def queue(status: Optional[str] = None, limit: int = 100):
    return {"ok": True, "rows": list_queue(status=status, limit=limit)}

class RunReq(BaseModel):
    default_price_cents: int = 2900

@router.post("/run_next", dependencies=[Depends(require_api_key)])
def runn(req: RunReq):
    return run_next(default_price_cents=req.default_price_cents)

@router.post("/export_catalog", dependencies=[Depends(require_api_key)])
def export():
    return export_catalog()
