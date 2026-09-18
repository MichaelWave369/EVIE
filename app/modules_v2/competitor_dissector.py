from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from app.modules.base import BaseModule
from .base import ModuleResult


class CompetitorDissector(BaseModule):
    name = "competitor_dissector"

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
        out_dir = Path(merged.get("output_dir") or run_folder) / "competitor_dissector"
        out_dir.mkdir(parents=True, exist_ok=True)
        competitors = merged.get("competitors") or ["Competitor A", "Competitor B"]
        if isinstance(competitors, str):
            competitors = [competitors]
        rows = []
        for c in competitors[:10]:
            c = str(c)
            rows.append(
                {
                    "name": c,
                    "positioning": f"{c} focuses on mainstream {topic} outcomes.",
                    "gap": f"Missing practical implementation layer for {topic}.",
                    "counter_position": f"Local-first + implementation-first {topic} playbooks.",
                }
            )
        payload = {"topic": topic, "status": "ok", "competitor_analysis": rows, "generated_at": datetime.utcnow().isoformat()}
        p = out_dir / f"competitor_dissector_{int(time.time())}.json"
        p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return ModuleResult(name=self.name, artifacts=[str(p)], summary=payload)
