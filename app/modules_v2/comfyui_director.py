from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from app.modules.base import BaseModule
from .base import ModuleResult
from .image_generator_v2 import ImageGeneratorV2
from .visual_fx_connectors import RenderFXConnector


class ComfyUIDirector(BaseModule):
    name = "comfyui_director"

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
        out_dir = Path(merged.get("output_dir") or run_folder) / "comfyui_director"
        out_dir.mkdir(parents=True, exist_ok=True)

        style = str(merged.get("style") or merged.get("image_style") or "cinematic")
        num_images = int(merged.get("num_images") or 3)
        final_assets_state_path = str(out_dir / "visual_final_assets.json")

        bridge_attempt = RenderFXConnector().enhance(
            image_paths=[str(p) for p in (merged.get("input_images") or [])],
            output_dir=out_dir / "bridge_handoff",
            style=style,
            job_type="comfyui_director_bridge",
            final_assets_state_path=final_assets_state_path,
            final_asset_category=str(merged.get("final_asset_category") or "final_thumbnail"),
        )

        payload: dict[str, Any] = {
            "topic": topic,
            "status": "ok",
            "mode": "bridge_first",
            "bridge_attempt": bridge_attempt,
            "generated_at": datetime.utcnow().isoformat(),
        }
        artifacts: list[str] = []

        if bridge_attempt.get("status") == "awaiting_external_processing":
            payload["status"] = "awaiting_external_processing"
            payload["image_paths"] = []
        else:
            img = ImageGeneratorV2().generate(
                topic=topic,
                run_folder=str(out_dir),
                sku=sku,
                tier=tier,
                price_cents=price_cents,
                platforms=platforms,
                constraints={**merged, "style": style, "num_images": num_images, "output_dir": str(out_dir)},
            )
            payload["mode"] = "comfyui_fallback"
            payload["image_paths"] = img.summary.get("image_paths") or []
            payload["prompts_used"] = img.summary.get("prompts_used") or []
            payload["comfyui_result"] = img.summary
            artifacts.extend(img.artifacts)

        sp = out_dir / f"comfyui_director_{int(time.time())}.json"
        sp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        artifacts.insert(0, str(sp))
        return ModuleResult(name=self.name, artifacts=artifacts, summary=payload)
