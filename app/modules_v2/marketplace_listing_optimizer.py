from __future__ import annotations
from typing import Any
import os

from .base import ModuleResult
from .utils import ensure_dir, write_text, write_json, slugify, three_six_nine_sections

class MarketplaceListingOptimizer:
    """Generates platform-ready listing variants (local templates).

    This is intentionally conservative: no claims, no hype, reusable copy blocks.
    """

    name = "marketplace_listing_optimizer"

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
        tslug = slugify(topic)
        out_dir = os.path.join(run_folder, "artifacts", self.name, tslug)
        ensure_dir(out_dir)

        base_title = constraints.get("listing_title") or f"{topic} ({tier})"
        audience = constraints.get("audience") or "people who want practical templates"
        promise = constraints.get("promise") or "A ready-to-use pack you can apply immediately"

        bullets3 = [
            "Clear outcome",
            "Usable templates",
            "Compounding workflow",
        ]
        bullets6 = [
            "Includes templates + checklists",
            "Local-first workflow",
            "Editable files",
            "Quickstart steps",
            "License + support info",
            "Platform upload checklist",
        ]
        bullets9 = [
            "No guarantees language included",
            "Great for beginners and operators",
            "Use as-is or customize",
            "Bundle-friendly",
            "Works with 369/Φ/Fib structure",
            "Add testimonials over time",
            "Price-test with 3 variants",
            "Improve titles every 8 days",
            "Keep everything local",
        ]

        md = three_six_nine_sections(f"Listing Copy — {base_title}", bullets3, bullets6, bullets9)
        md += f"\n\n## Description\n\n**For:** {audience}\n\n**What it is:** {promise}.\n\n**What you get:**\n- Organized folders\n- Templates + checklists\n- A simple plan to ship\n\n**Disclaimer:** This is a template/guidance pack. Results depend on execution and market conditions.\n"

        fields = {
            "sku": sku,
            "title": base_title,
            "tier": tier,
            "price_cents": price_cents,
            "platforms": platforms,
            "tags": ["templates", "checklist", "workflow", "local-first"],
            "bullets": bullets6,
            "disclaimer": "Template/guidance pack. No guarantees.",
        }

        md_path = os.path.join(out_dir, "LISTING_COPY.md")
        json_path = os.path.join(out_dir, "FIELDS.json")
        write_text(md_path, md)
        write_json(json_path, fields)

        return ModuleResult(self.name, [md_path, json_path], {"ok": True, "title": base_title})
