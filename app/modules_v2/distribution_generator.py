from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from app.modules.base import BaseModule
from .base import ModuleResult


class DistributionGenerator(BaseModule):
    name = "distribution_generator"

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
        merged.setdefault("output_dir", run_folder)

        wf_meta = merged.get("workflow_step_metadata") or {}
        hooks = ((wf_meta.get("hooks_generator") or {}).get("hooks") or [])
        product = wf_meta.get("product_packager") or {}
        product_name = product.get("product_name") or f"{topic} Money Pack"

        payload = {
            "topic": topic,
            "youtube_title": f"{topic}: The Complete Money Pack Breakdown",
            "youtube_description": (
                f"In this video, we break down the {product_name} and show how to apply it immediately.\n\n"
                "Includes actionable steps, templates, and next actions."
            ),
            "youtube_tags": [topic, "money pack", "creator business", "digital product"],
            "youtube_pinned_comment": f"Want the full {product_name}? Reply 'PACK' and I’ll send details.",
            "youtube_cta": "Download the full pack and launch your version this week.",
            "thumbnail_ideas": [
                f"Before/After: {topic}",
                f"The {topic} framework that pays",
                f"Build your {topic} money pack in 1 week",
            ],
            "twitter_launch_post": f"I turned {topic} into a reusable money pack. Here’s the system 👇",
            "twitter_thread": [
                f"1/ If you want to turn {topic} into revenue, start with one reusable pack.",
                "2/ Build once: script + slides + infographic + study content.",
                "3/ Repurpose across video, social, and email.",
                f"4/ Package it, price it, and ship. {product_name} is the blueprint.",
                "5/ Consistency compounds. Publish weekly.",
            ],
            "twitter_cta_variants": [
                "Reply 'PACK' and I’ll send the breakdown.",
                "DM me 'MONEY PACK' for the template.",
                "Comment and I’ll share the build checklist.",
            ],
            "newsletter_draft": (
                f"Today: how to turn {topic} into one product and multiple channels.\n\n"
                "I’m sharing the framework, assets, and launch plan."
            ),
            "email_promo": (
                f"Subject: New {topic} money pack\n\n"
                f"I just packaged a complete {topic} asset bundle you can use immediately. "
                "Reply and I’ll send the details."
            ),
            "email_cta_variants": [
                "Get the full pack",
                "See the launch checklist",
                "Access the creator bundle",
            ],
            "tiktok_hooks": hooks[:5] or [
                f"3 things nobody tells you about {topic}",
                f"How I packaged {topic} into a sellable bundle",
            ],
            "instagram_caption": (
                f"I packaged {topic} into a repeatable creator system. "
                "If you want the full workflow, comment PACK."
            ),
            "linkedin_post": (
                f"Built a practical {topic} money-pack workflow: ideation, assets, distribution, and monetization."
            ),
            "reel_short_captions": [
                f"{topic} in 30 seconds",
                "Build once, publish everywhere",
                "From content to money pack",
            ],
            "hooks_used": hooks[:5],
            "generated_at": datetime.utcnow().isoformat(),
        }

        out_dir = Path(merged.get("output_dir") or "data/artifacts/distribution")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"distribution_{re.sub(r'[^a-z0-9]+', '_', topic.lower())[:40]}.json"
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        return ModuleResult(name=self.name, artifacts=[str(out_path)], summary=payload)
