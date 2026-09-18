from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List

from app.security.auth import require_api_key
from app.db import queries

router = APIRouter(prefix="/v1/evidence", tags=["evidence"])


class EvidenceCreateReq(BaseModel):
    kind: str
    title: str
    campaign_id: Optional[int] = None
    product_id: Optional[int] = None
    session_id: Optional[int] = None
    url: Optional[str] = None
    content: Optional[str] = None
    file_path: Optional[str] = None
    sensitive: bool = False
    tags: List[str] = []


@router.get("", dependencies=[Depends(require_api_key)])
def list_evidence(limit: int = 200, campaign_id: Optional[int] = None, product_id: Optional[int] = None):
    return {"evidence": queries.list_evidence(campaign_id=campaign_id, product_id=product_id, limit=limit)}


@router.post("/create", dependencies=[Depends(require_api_key)])
def create_evidence(req: EvidenceCreateReq):
    eid = queries.create_evidence(
        campaign_id=req.campaign_id,
        product_id=req.product_id,
        session_id=req.session_id,
        kind=req.kind,
        title=req.title,
        url=req.url,
        content=req.content,
        file_path=req.file_path,
        sensitive=req.sensitive,
        tags=req.tags,
    )
    return {"evidence_id": eid}
