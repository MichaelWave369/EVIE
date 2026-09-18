from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional

from app.security.auth import require_api_key
from app.workflows.runner import list_workflows, run_workflow

router = APIRouter(prefix="/v1/workflows", tags=["workflows"])


@router.get("", dependencies=[Depends(require_api_key)])
def workflows():
    return {"workflows": list_workflows()}


class WorkflowRunReq(BaseModel):
    topic: str
    constraints: Dict[str, Any] = {}
    campaign_id: Optional[int] = None
    session_id: Optional[int] = None
    dry_run: bool = False


@router.post("/{name}/run", dependencies=[Depends(require_api_key)])
def run(name: str, req: WorkflowRunReq):
    try:
        res = run_workflow(
            name,
            topic=req.topic,
            constraints=req.constraints,
            actor="api",
            campaign_id=req.campaign_id,
            session_id=req.session_id,
            dry_run=req.dry_run,
        )
        return res
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
