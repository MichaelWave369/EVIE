from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional, List

from app.security.auth import require_api_key
from app.db import queries

router = APIRouter(prefix="/v1/campaigns", tags=["campaigns"])


class CampaignCreateReq(BaseModel):
    name: str
    niche: Optional[str] = None
    audience: Optional[str] = None
    promise: Optional[str] = None
    platforms: Dict[str, Any] = {}
    status: str = "active"
    metadata: Dict[str, Any] = {}
    campaign_key: Optional[str] = None


@router.get("", dependencies=[Depends(require_api_key)])
def list_campaigns(limit: int = 100):
    return {"campaigns": queries.list_campaigns(limit=limit)}


@router.post("/create", dependencies=[Depends(require_api_key)])
def create_campaign(req: CampaignCreateReq):
    cid = queries.create_campaign(
        name=req.name,
        niche=req.niche,
        audience=req.audience,
        promise=req.promise,
        platforms=req.platforms,
        status=req.status,
        metadata=req.metadata,
        campaign_key=req.campaign_key,
    )
    return {"campaign_id": cid}


@router.get("/{campaign_id}", dependencies=[Depends(require_api_key)])
def get_campaign(campaign_id: int):
    try:
        c = queries.get_campaign(int(campaign_id))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    sessions = queries.list_sessions(campaign_id=int(campaign_id), limit=200)
    evidence = queries.list_evidence(campaign_id=int(campaign_id), limit=200)
    return {"campaign": c, "sessions": sessions, "evidence": evidence}


class SessionCreateReq(BaseModel):
    name: str
    notes: Optional[str] = None
    status: str = "open"


@router.get("/{campaign_id}/sessions", dependencies=[Depends(require_api_key)])
def list_campaign_sessions(campaign_id: int, limit: int = 200):
    return {"sessions": queries.list_sessions(campaign_id=int(campaign_id), limit=limit)}


@router.post("/{campaign_id}/sessions/create", dependencies=[Depends(require_api_key)])
def create_campaign_session(campaign_id: int, req: SessionCreateReq):
    sid = queries.create_session(int(campaign_id), req.name, notes=req.notes, status=req.status)
    return {"session_id": sid}


@router.get("/{campaign_id}/evidence", dependencies=[Depends(require_api_key)])
def list_campaign_evidence(campaign_id: int, limit: int = 200):
    return {"evidence": queries.list_evidence(campaign_id=int(campaign_id), limit=limit)}
