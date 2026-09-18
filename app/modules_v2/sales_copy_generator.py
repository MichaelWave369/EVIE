from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from app.modules.base import BaseModule
from .base import ModuleResult


class SalesCopyGenerator(BaseModule):
    name = "sales_copy_generator"

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
        product = wf_meta.get("product_packager") or {}
        product_name = str(merged.get("product_name") or product.get("product_name") or f"{topic} Money Pack")

        payload = {
            "topic": topic,
            "headline": f"Turn {topic} into momentum in one focused pack",
            "full_description": (
                f"{product_name} gives you a complete, practical system for learning and shipping around {topic}. "
                "Use the scripts, visuals, and study assets to create, teach, and sell faster."
            ),
            "bullet_points": [
                "Ready-to-use lesson and media assets",
                "Structured for fast publishing and repurposing",
                "Built to convert learning into revenue actions",
                "Local-first workflow with reusable outputs",
            ],
            "call_to_action": "Get the pack and launch your first version this week.",
            "generated_at": datetime.utcnow().isoformat(),
        }

        out_dir = Path(merged.get("output_dir") or "data/artifacts/sales_copy")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"sales_copy_{re.sub(r'[^a-z0-9]+', '_', topic.lower())[:40]}.json"
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        return ModuleResult(name=self.name, artifacts=[str(out_path)], summary=payload)
