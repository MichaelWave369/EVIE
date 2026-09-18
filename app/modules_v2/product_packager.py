from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from app.modules.base import BaseModule
from .base import ModuleResult


class ProductPackager(BaseModule):
    name = "product_packager"

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
        artifact_paths = [str(p) for p in (merged.get("artifact_paths") or [])]

        bundle_contents = [Path(p).name for p in artifact_paths if p]
        if not bundle_contents:
            bundle_contents = ["podcast script", "slides", "infographic", "study assets"]

        suggested_price = 19 if len(bundle_contents) < 4 else (29 if len(bundle_contents) < 7 else 49)
        product_name = f"{topic} Money Pack"
        payload = {
            "topic": topic,
            "product_name": product_name,
            "product_description": f"A practical, ready-to-use content and learning bundle for {topic}.",
            "bundle_contents": bundle_contents,
            "price_suggestion": f"${suggested_price}",
            "generated_at": datetime.utcnow().isoformat(),
        }

        out_dir = Path(merged.get("output_dir") or "data/artifacts/product_packager")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"product_pack_{re.sub(r'[^a-z0-9]+', '_', topic.lower())[:40]}.json"
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        return ModuleResult(name=self.name, artifacts=[str(out_path)], summary=payload)
