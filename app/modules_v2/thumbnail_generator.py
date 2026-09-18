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


class ThumbnailGenerator(BaseModule):
    name = "thumbnail_generator"

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
        title = str(merged.get("title") or topic).strip()
        hook = str(merged.get("hook") or f"{topic} breakthrough").strip()
        style = str(merged.get("style") or merged.get("image_style") or "cinematic").strip().lower()
        num_variants = int(merged.get("num_variants") or merged.get("num_images") or 4)

        out_dir = Path(merged.get("output_dir") or run_folder) / "thumbnails"
        out_dir.mkdir(parents=True, exist_ok=True)
        final_assets_state_path = out_dir / "visual_final_assets.json"

        base_prompts = [
            f"YouTube thumbnail, {style}, topic: {topic}, title concept: {title}, hook: {hook}, big focal subject, high contrast, no watermark, variant {i+1}"
            for i in range(max(1, min(num_variants, 8)))
        ]

        image_res = ImageGeneratorV2().generate(
            topic=topic,
            run_folder=str(out_dir),
            sku=sku,
            tier=tier,
            price_cents=price_cents,
            platforms=platforms,
            constraints={
                **merged,
                "output_dir": str(out_dir),
                "style": style,
                "num_images": num_variants,
                "custom_prompts": base_prompts,
            },
        )
        image_paths = list(image_res.summary.get("image_paths") or [])

        render_fx = RenderFXConnector().enhance(image_paths, output_dir=out_dir / "render_fx", style=style, job_type="thumbnail_polish", final_assets_state_path=str(final_assets_state_path), final_asset_category="final_thumbnail")
        enhanced_paths = list(render_fx.get("enhanced_paths") or image_paths)

        vector_fx = VectorFXConnector().polish(enhanced_paths, output_dir=out_dir / "vector_fx", job_type="thumbnail_polish", final_assets_state_path=str(final_assets_state_path), final_asset_category="final_thumbnail")
        polished_paths = list(vector_fx.get("polished_paths") or enhanced_paths)

        rank_res = VisualRanker().generate(
            topic=topic,
            run_folder=str(out_dir),
            sku=sku,
            tier=tier,
            price_cents=price_cents,
            platforms=platforms,
            constraints={"image_paths": polished_paths, "title": title, "hook": hook, "ranking_job_type": "thumbnail_rank", "final_assets_state_path": str(final_assets_state_path), "final_asset_category": "final_thumbnail"},
        )

        ranking = rank_res.summary.get("ranked_images") or []
        best = rank_res.summary.get("best_image_path") or (polished_paths[0] if polished_paths else "")

        text_safe_notes = [
            "Keep text inside central 70% safe area.",
            "Avoid placing critical words in extreme corners.",
            "Prefer high foreground/background contrast for readability.",
        ]

        preferred_state = set_preferred_asset(final_assets_state_path, category="final_thumbnail", asset_path=best, source=self.name, note="Auto-selected best generated thumbnail") if best else {}

        payload = {
            "topic": topic,
            "title": title,
            "hook": hook,
            "style": style,
            "status": "generated" if polished_paths else "unavailable",
            "ranked_thumbnail_paths": [r.get("path") for r in ranking if r.get("path")],
            "best_thumbnail_path": best,
            "prompts_used": image_res.summary.get("prompts_used") or base_prompts,
            "ranking_metadata": {
                "method": rank_res.summary.get("ranking_method"),
                "ranked_images": ranking,
            },
            "text_safe_composition_notes": text_safe_notes,
            "tool_chain": {
                "image_generator_v2": image_res.summary.get("status"),
                "render_fx": render_fx.get("status"),
                "vector_fx": vector_fx.get("status"),
                "vision_fx": (rank_res.summary.get("vision_fx") or {}).get("status"),
            },
            "handoff_jobs": {
                "render_fx": {"job_id": render_fx.get("job_id"), "job_folder": render_fx.get("job_folder"), "output_folder": render_fx.get("output_folder")},
                "vector_fx": {"job_id": vector_fx.get("job_id"), "job_folder": vector_fx.get("job_folder"), "output_folder": vector_fx.get("output_folder")},
                "vision_fx": {"job_id": (rank_res.summary.get("vision_fx") or {}).get("job_id"), "job_folder": (rank_res.summary.get("vision_fx") or {}).get("job_folder"), "output_folder": (rank_res.summary.get("vision_fx") or {}).get("output_folder")},
            },
            "preferred_final_asset": ((preferred_state.get("preferred_assets") or {}).get("final_thumbnail") or {}).get("asset_path", ""),
            "final_asset_state_path": str(final_assets_state_path),
            "generated_at": datetime.utcnow().isoformat(),
        }

        summary_path = out_dir / f"thumbnail_generation_{re.sub(r'[^a-z0-9]+', '_', topic.lower())[:40]}_{int(time.time())}.json"
        summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        artifacts = [str(summary_path), *polished_paths, *image_res.artifacts, *rank_res.artifacts]
        return ModuleResult(name=self.name, artifacts=artifacts, summary=payload)
