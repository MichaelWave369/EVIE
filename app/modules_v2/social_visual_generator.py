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
from .visual_final_assets import set_preferred_asset


class SocialVisualGenerator(BaseModule):
    name = "social_visual_generator"

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
        channel = str(merged.get("channel") or "x").strip().lower()
        style = str(merged.get("style") or merged.get("image_style") or "social").strip().lower()
        num_images = int(merged.get("num_images") or merged.get("num_variants") or 4)
        supported_channels = ["x", "instagram", "linkedin", "tiktok"]
        if channel not in supported_channels:
            channel = "x"

        out_dir = Path(merged.get("output_dir") or run_folder) / "social_visuals"
        out_dir.mkdir(parents=True, exist_ok=True)
        final_assets_state_path = out_dir / "visual_final_assets.json"

        prompts = [
            f"social promo visual for {channel}, {style}, topic {topic}, punchy headline area, clean CTA zone, variant {i+1}"
            for i in range(max(1, min(num_images, 8)))
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

        render = RenderFXConnector().enhance(base.summary.get("image_paths") or [], output_dir=out_dir / "render_fx", style=style, job_type="social_visual_finish", final_assets_state_path=str(final_assets_state_path), final_asset_category="final_social_visual")
        polished = VectorFXConnector().polish(render.get("enhanced_paths") or [], output_dir=out_dir / "vector_fx", job_type="social_visual_finish", final_assets_state_path=str(final_assets_state_path), final_asset_category="final_social_visual")

        preferred_path = ((polished.get("polished_paths") or [""])[0])
        preferred_state = set_preferred_asset(final_assets_state_path, category="final_social_visual", asset_path=preferred_path, source=self.name, note="Auto-selected first generated social visual") if preferred_path else {}

        payload = {
            "topic": topic,
            "status": "generated" if (polished.get("polished_paths") or []) else "unavailable",
            "channel": channel,
            "social_visual_paths": polished.get("polished_paths") or [],
            "prompts_used": base.summary.get("prompts_used") or prompts,
            "style_notes": {
                "x": "bold focal point + concise text area",
                "instagram": "high-contrast visual-first composition",
                "linkedin": "clean professional layout",
                "tiktok": "dynamic vertical-friendly composition",
            }.get(channel),
            "preferred_final_asset": ((preferred_state.get("preferred_assets") or {}).get("final_social_visual") or {}).get("asset_path", ""),
            "final_asset_state_path": str(final_assets_state_path),
            "generated_at": datetime.utcnow().isoformat(),
            "tool_chain": {
                "image_generator_v2": base.summary.get("status"),
                "render_fx": render.get("status"),
                "vector_fx": polished.get("status"),
            },
            "handoff_jobs": {
                "render_fx": {"job_id": render.get("job_id"), "job_folder": render.get("job_folder"), "output_folder": render.get("output_folder")},
                "vector_fx": {"job_id": polished.get("job_id"), "job_folder": polished.get("job_folder"), "output_folder": polished.get("output_folder")},
            },
        }
        summary_path = out_dir / f"social_visual_generation_{re.sub(r'[^a-z0-9]+', '_', topic.lower())[:40]}_{int(time.time())}.json"
        summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        artifacts = [str(summary_path), *(polished.get("polished_paths") or []), *base.artifacts]
        return ModuleResult(name=self.name, artifacts=artifacts, summary=payload)
