from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from app.modules.base import BaseModule
from .base import ModuleResult


class SalesPageBuilder(BaseModule):
    name = "sales_page_builder"

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
        out_dir = Path(merged.get("output_dir") or run_folder) / "sales_page_builder"
        out_dir.mkdir(parents=True, exist_ok=True)

        product_name = str(merged.get("product_name") or f"{topic} Revenue Kit")
        audience = str(merged.get("audience") or "creators")
        price = str(merged.get("price") or "$29")

        page = {
            "headline": f"Build a repeatable {topic} system without guesswork",
            "subheadline": f"A practical, local-first framework for {audience}.",
            "offer_stack": [
                f"{product_name} core playbook",
                "launch checklist",
                "copy templates",
            ],
            "guarantee": "14-day implementation guarantee",
            "price": price,
            "cta": "Get Instant Access",
            "platform_blocks": {
                "gumroad": {"short_pitch": f"{product_name} helps you ship faster.", "price": price},
                "payhip": {"short_pitch": f"{product_name} makes launch execution easier.", "price": price},
                "storefront": {"hero_title": f"{product_name}", "hero_cta": "Start Now"},
            },
        }

        md = [
            f"# {page['headline']}",
            "",
            page["subheadline"],
            "",
            "## What You Get",
            *[f"- {x}" for x in page["offer_stack"]],
            "",
            f"## Price\n{price}",
            "",
            f"## Guarantee\n{page['guarantee']}",
            "",
            f"## CTA\n{page['cta']}",
        ]

        md_path = out_dir / "sales_page.md"
        json_path = out_dir / "sales_page.json"
        md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
        json_path.write_text(json.dumps(page, indent=2), encoding="utf-8")

        summary = {"topic": topic, "status": "ok", "sales_page": page, "generated_at": datetime.utcnow().isoformat()}
        summary_path = out_dir / f"sales_page_builder_{int(time.time())}.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return ModuleResult(name=self.name, artifacts=[str(summary_path), str(md_path), str(json_path)], summary=summary)
