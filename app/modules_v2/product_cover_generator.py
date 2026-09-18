from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from app.modules.base import BaseModule

from .base import ModuleResult
from .image_generator_v2 import ImageGeneratorV2
from .visual_fx_connectors import RenderFXConnector, VectorFXConnector
from .visual_ranker import VisualRanker
from .visual_final_assets import set_preferred_asset


class ProductCoverGenerator(BaseModule):
    name = "product_cover_generator"

    def generate(
        self,
        *,
        topic: str,
        run_folder: str,
        sku: str,
        tier: str,
        price_cents: int,
        platforms: list[str],
        constraints: dict[str, Any],
    ) -> ModuleResult:
        merged = dict(constraints or {})
        style = str(merged.get("style") or merged.get("image_style") or "product").strip().lower()
        num_images = int(merged.get("num_images") or 3)
        product_name = str(merged.get("product_name") or f"{topic} Toolkit")
        out_dir = Path(merged.get("output_dir") or run_folder) / "product_covers"
        out_dir.mkdir(parents=True, exist_ok=True)
        final_assets_state_path = out_dir / "visual_final_assets.json"

        prompts = [
            f"premium digital product cover, {style}, {product_name}, topic {topic}, clean typography space, ecommerce hero visual, variant {i+1}"
            for i in range(max(1, min(num_images, 6)))
        ]

        base = ImageGeneratorV2().generate(
            topic=topic,
            run_folder=str(out_dir),
            sku=sku,
            tier=tier,
            price_cents=price_cents,
            platforms=platforms,
            constraints={**merged, "output_dir": str(out_dir), "style": style, "num_images": num_images, "custom_prompts": prompts},
        )
        render = RenderFXConnector().enhance(base.summary.get("image_paths") or [], output_dir=out_dir / "render_fx", style=style, job_type="product_cover_finish", final_assets_state_path=str(final_assets_state_path), final_asset_category="final_product_cover")
        polished = VectorFXConnector().polish(render.get("enhanced_paths") or [], output_dir=out_dir / "vector_fx", job_type="product_cover_finish", final_assets_state_path=str(final_assets_state_path), final_asset_category="final_product_cover")

        ranked = VisualRanker().generate(
            topic=topic,
            run_folder=str(out_dir),
            sku=sku,
            tier=tier,
            price_cents=price_cents,
            platforms=platforms,
            constraints={"image_paths": polished.get("polished_paths") or [], "title": product_name, "hook": "cover", "ranking_job_type": "product_cover_finish", "final_assets_state_path": str(final_assets_state_path), "final_asset_category": "final_product_cover"},
        )

        preferred_path = ranked.summary.get("best_image_path") or ""
        preferred_state = set_preferred_asset(final_assets_state_path, category="final_product_cover", asset_path=preferred_path, source=self.name, note="Auto-selected best generated product cover") if preferred_path else {}

        payload = {
            "topic": topic,
            "status": "generated" if (polished.get("polished_paths") or []) else "unavailable",
            "product_cover_paths": [x.get("path") for x in (ranked.summary.get("ranked_images") or []) if x.get("path")],
            "hero_image_path": ranked.summary.get("best_image_path") or "",
            "prompts_used": base.summary.get("prompts_used") or prompts,
            "ranking_metadata": ranked.summary,
            "platform_targets": ["gumroad", "payhip"],
            "preferred_final_asset": ((preferred_state.get("preferred_assets") or {}).get("final_product_cover") or {}).get("asset_path", ""),
            "final_asset_state_path": str(final_assets_state_path),
            "generated_at": datetime.utcnow().isoformat(),
            "handoff_jobs": {
                "render_fx": {"job_id": render.get("job_id"), "job_folder": render.get("job_folder"), "output_folder": render.get("output_folder")},
                "vector_fx": {"job_id": polished.get("job_id"), "job_folder": polished.get("job_folder"), "output_folder": polished.get("output_folder")},
                "vision_fx": {"job_id": (ranked.summary.get("vision_fx") or {}).get("job_id"), "job_folder": (ranked.summary.get("vision_fx") or {}).get("job_folder"), "output_folder": (ranked.summary.get("vision_fx") or {}).get("output_folder")},
            },
        }
        summary_path = out_dir / f"product_cover_generation_{re.sub(r'[^a-z0-9]+', '_', topic.lower())[:40]}_{int(time.time())}.json"
        summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        artifacts = [str(summary_path), *(polished.get("polished_paths") or []), *base.artifacts, *ranked.artifacts]
        return ModuleResult(name=self.name, artifacts=artifacts, summary=payload)
