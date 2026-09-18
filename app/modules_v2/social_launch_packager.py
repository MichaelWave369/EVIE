from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from app.modules.base import BaseModule
from .base import ModuleResult


class SocialLaunchPackager(BaseModule):
    name = "social_launch_packager"

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
        if not bool(merged.get("export_social_pack", True)):
            payload = {
                "topic": topic,
                "status": "skipped",
                "message": "export_social_pack disabled",
                "generated_at": datetime.utcnow().isoformat(),
            }
            out_dir = Path(merged.get("output_dir") or run_folder)
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"social_launch_pack_{re.sub(r'[^a-z0-9]+', '_', topic.lower())[:40]}.json"
            out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return ModuleResult(name=self.name, artifacts=[str(out_path)], summary=payload)

        wf_meta = merged.get("workflow_step_metadata") or {}
        dist = wf_meta.get("distribution_generator") or {}

        payload = {
            "topic": topic,
            "status": "exported",
            "x_launch_post": dist.get("twitter_launch_post", f"Just shipped a {topic} launch bundle. Here's the playbook."),
            "x_thread": dist.get("twitter_thread")
            or [
                f"1/ Build your {topic} engine once.",
                "2/ Repurpose into social + video + email.",
                "3/ Launch weekly and iterate.",
            ],
            "tiktok_caption": (dist.get("tiktok_hooks") or [f"How I launched {topic} this week"])[0],
            "instagram_caption": dist.get("instagram_caption", f"Shipped: {topic} launch pack. Comment PACK for details."),
            "linkedin_post": dist.get("linkedin_post", f"Built and shipped a {topic} weekly launch workflow."),
            "cta_variants": dist.get("twitter_cta_variants")
            or ["Reply PACK", "DM LAUNCH", "Comment for checklist"],
            "shortform_launch_snippets": dist.get("reel_short_captions")
            or [f"{topic} launch in 30s", "Build once, distribute everywhere"],
            "generated_at": datetime.utcnow().isoformat(),
        }

        out_dir = Path(merged.get("output_dir") or run_folder)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"social_launch_pack_{re.sub(r'[^a-z0-9]+', '_', topic.lower())[:40]}.json"
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return ModuleResult(name=self.name, artifacts=[str(out_path)], summary=payload)
