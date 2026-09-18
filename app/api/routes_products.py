from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from app.security.auth import require_api_key
from app.db import queries

router = APIRouter(prefix="/v1/products", tags=["products"])

class ProductCreateReq(BaseModel):
    module: str
    sku: str
    name: str
    description: Optional[str] = None
    price_cents: int = 0
    status: str = "draft"
    metadata: Dict[str, Any] = {}
    campaign_id: Optional[int] = None
    session_id: Optional[int] = None

@router.get("", dependencies=[Depends(require_api_key)])
def list_products():
    return {"products": queries.list_products()}

@router.get("/{product_id}", dependencies=[Depends(require_api_key)])
def get_product(product_id: int):
    try:
        p = queries.get_product(product_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    assets = queries.list_assets(product_id)
    return {"product": p, "assets": assets}

@router.post("/create", dependencies=[Depends(require_api_key)])
def create_product(req: ProductCreateReq):
    pid = queries.create_product(req.module, req.sku, req.name, req.description, req.price_cents, req.status, req.metadata, campaign_id=req.campaign_id, session_id=req.session_id)
    return {"product_id": pid}

class AttachReq(BaseModel):
    asset_type: str
    path: str

@router.post("/{product_id}/attach", dependencies=[Depends(require_api_key)])
def attach_asset(product_id: int, req: AttachReq):
    aid = queries.attach_asset(int(product_id), req.asset_type, req.path)
    return {"asset_id": aid}


@router.get("/{product_id}/versions")
def product_versions(product_id: int, api_key: str = Depends(require_api_key)):
    if not queries.get_product(product_id):
        raise HTTPException(status_code=404, detail="Product not found")
    return {"product_id": int(product_id), "versions": queries.list_product_versions(int(product_id))}


from app.export.product_packet import build_product_packet

@router.post("/{product_id}/packet", dependencies=[Depends(require_api_key)])
def product_packet(product_id: int):
    """Generate a Product Packet (PDF + zip) for sharing/sales or audits."""
    try:
        p = queries.get_product(int(product_id))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    pkt = build_product_packet(int(product_id))
    return {"product": p, "packet": pkt}
