from __future__ import annotations
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from app.security.auth import require_api_key
from app.flywheel.builder import build_offer
from app.flywheel.runctx import RunContext
from app.db import queries

router = APIRouter(prefix="/v1/flywheel", tags=["flywheel"])

class OfferReq(BaseModel):
    topic: str
    modules: List[str] = ["ebooks","templates","ecosystem_template_packs","microcourse","leadmagnet","newsletter","youtube","repurposer","offer_ladder","conversion_packager","funnel_engine","platform_packs","seo_engine","affiliate","affiliate_site_mode","affiliate_tables_generator","directory","membership_automation","membership_issue_generator","community","marketplace_listing_optimizer","brandkit_cover_factory","creative_factory","localization_engine","programmatic_seo_generator","pod_pack_generator","pod_superpack","pod","miniapp","micro_tool_generator","extension","terms_generator","ab_kit_generator","dataset_to_product_pipeline","licensing_matrix_generator","storefront_html_generator","storefront_site_builder","affiliate_comparison_scale","onboarding_automation","support_refund_autopack","offer_qa_gate"]
    constraints_by_module: Dict[str, Dict[str, Any]] = {}
    name: Optional[str] = None
    description: Optional[str] = None
    price_cents: int = 2900
    tier: str = "core"
    tier_rules_path: Optional[str] = None

@router.post("/offer", dependencies=[Depends(require_api_key)])
def offer(req: OfferReq):
    run_id = queries.create_run(
        run_type="offer",
        module="bundle",
        topic=req.topic,
        input_obj={"topic": req.topic, "modules": req.modules, "constraints_by_module": req.constraints_by_module, "price_cents": req.price_cents, "tier": req.tier},
        actor="api",
    )
    run_ctx = RunContext(run_id=run_id, actor="api")
    res = build_offer(
        topic=req.topic,
        modules=req.modules,
        constraints_by_module=req.constraints_by_module,
        name=req.name,
        description=req.description,
        price_cents=req.price_cents,
        tier=req.tier,
        tier_rules_path=req.tier_rules_path,
        run_ctx=run_ctx,
    )
    return {
        "run_id": run_id,
        "product_id": res.product_id,
        "sku": res.sku,
        "bundle_zip": res.bundle_zip,
        "gumroad_dir": res.gumroad_dir,
        "module_runs": res.module_runs,
    }
