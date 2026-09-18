from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from app.modules.base import BaseModule
from .base import ModuleResult


class PayhipPackager(BaseModule):
    name = "payhip_packager"

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
        if not bool(merged.get("export_payhip_pack", True)):
            payload = {
                "topic": topic,
                "status": "skipped",
                "message": "export_payhip_pack disabled",
                "generated_at": datetime.utcnow().isoformat(),
            }
            out_dir = Path(merged.get("output_dir") or run_folder)
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"payhip_pack_{re.sub(r'[^a-z0-9]+', '_', topic.lower())[:40]}.json"
            out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return ModuleResult(name=self.name, artifacts=[str(out_path)], summary=payload)

        wf_meta = merged.get("workflow_step_metadata") or {}
        product = wf_meta.get("product_packager") or {}
        sales = wf_meta.get("sales_copy_generator") or {}
        artifacts = [str(a) for a in (merged.get("artifact_paths") or [])]

        payload = {
            "topic": topic,
            "status": "exported",
            "product_title": product.get("product_name") or f"{topic} Membership Bundle",
            "short_description": product.get("product_description") or f"A practical {topic} bundle for creators.",
            "long_description": sales.get("full_description") or f"Complete weekly {topic} bundle with premium assets and launch copy.",
            "bullet_benefits": sales.get("bullet_points") or [
                "Weekly creator-ready issue and launch copy",
                "Premium bonus assets for members",
                "Reusable templates to speed up publishing",
            ],
            "price_suggestion": product.get("price_suggestion") or "$19",
            "category_tags": [topic.lower(), "membership", "newsletter", "digital product"],
            "upload_checklist": [
                "Set product title and short description",
                "Paste long description and bullet benefits",
                "Upload bundle files listed below",
                "Set price and checkout settings",
                "Publish listing and connect CTA links",
            ],
            "bundle_file_references": artifacts[:20],
            "generated_at": datetime.utcnow().isoformat(),
        }

        out_dir = Path(merged.get("output_dir") or run_folder)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"payhip_pack_{re.sub(r'[^a-z0-9]+', '_', topic.lower())[:40]}.json"
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return ModuleResult(name=self.name, artifacts=[str(out_path)], summary=payload)
