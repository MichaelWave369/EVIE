from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from app.modules.base import BaseModule
from .base import ModuleResult


class NewsletterPackager(BaseModule):
    name = "newsletter_packager"

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
        if not bool(merged.get("export_newsletter_pack", True)):
            payload = {
                "topic": topic,
                "status": "skipped",
                "message": "export_newsletter_pack disabled",
                "generated_at": datetime.utcnow().isoformat(),
            }
            out_dir = Path(merged.get("output_dir") or run_folder)
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"newsletter_pack_{re.sub(r'[^a-z0-9]+', '_', topic.lower())[:40]}.json"
            out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return ModuleResult(name=self.name, artifacts=[str(out_path)], summary=payload)

        wf_meta = merged.get("workflow_step_metadata") or {}
        dist = wf_meta.get("distribution_generator") or {}
        product = wf_meta.get("product_packager") or {}
        product_name = product.get("product_name") or f"{topic} Membership Bonus"

        payload = {
            "topic": topic,
            "status": "exported",
            "newsletter_issue_draft": dist.get(
                "newsletter_draft",
                f"This week in {topic}: what worked, what changed, and how to apply it fast.",
            ),
            "free_version_teaser": (
                f"Free issue preview: this week we cover one quick-win from {topic} you can apply in 10 minutes."
            ),
            "premium_version_section": (
                f"Premium members get the full walkthrough, implementation checklist, and bonus asset pack: {product_name}."
            ),
            "upgrade_cta": "Upgrade to premium to unlock full templates and weekly bonus downloads.",
            "short_promo_email": dist.get(
                "email_promo",
                f"Subject: New {topic} member issue\n\nI just published this week's {topic} issue with a new bonus pack."
            ),
            "cta_variants": dist.get("email_cta_variants")
            or ["Upgrade to premium", "Get this week's member pack", "Unlock the bonus assets"],
            "subject_line_options": [
                f"{topic}: this week's member brief",
                f"New premium {topic} issue + bonus",
                f"Your weekly {topic} implementation pack",
            ],
            "beehiiv_export": {
                "post_title": f"{topic} Weekly Member Brief",
                "post_body_markdown": dist.get("newsletter_draft", ""),
                "free_teaser_block": "\n\n**Free Preview:** One quick-win strategy from this issue.",
                "premium_block": "\n\n**Premium Section:** Full walkthrough + downloadable assets.",
            },
            "convertkit_export": {
                "broadcast_subject": f"New {topic} premium issue",
                "broadcast_body_text": dist.get("email_promo", ""),
                "button_cta_options": dist.get("email_cta_variants") or [],
            },
            "generated_at": datetime.utcnow().isoformat(),
        }

        out_dir = Path(merged.get("output_dir") or run_folder)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"newsletter_pack_{re.sub(r'[^a-z0-9]+', '_', topic.lower())[:40]}.json"
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return ModuleResult(name=self.name, artifacts=[str(out_path)], summary=payload)
