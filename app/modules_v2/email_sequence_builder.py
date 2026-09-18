from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from app.modules.base import BaseModule
from .base import ModuleResult


class EmailSequenceBuilder(BaseModule):
    name = "email_sequence_builder"

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
        out_dir = Path(merged.get("output_dir") or run_folder) / "email_sequence_builder"
        out_dir.mkdir(parents=True, exist_ok=True)

        n = max(3, min(10, int(merged.get("emails") or 5)))
        product_name = str(merged.get("product_name") or f"{topic} Revenue Kit")

        seq = []
        for i in range(1, n + 1):
            seq.append(
                {
                    "day": i,
                    "subject": f"{topic} email {i}: practical win",
                    "preview": f"A short tactical step for {topic} progress.",
                    "body": f"Day {i} for {product_name}: teach one concrete action and end with CTA.",
                    "cta": "Reply with your blocker or grab the full kit",
                }
            )

        payload = {
            "topic": topic,
            "status": "ok",
            "email_sequence": seq,
            "exports": {
                "beehiiv": {"posts": seq},
                "convertkit": {"broadcasts": seq},
                "mailerlite": {"campaigns": seq},
            },
            "generated_at": datetime.utcnow().isoformat(),
        }

        path = out_dir / "email_sequence.json"
        summary_path = out_dir / f"email_sequence_builder_{int(time.time())}.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return ModuleResult(name=self.name, artifacts=[str(summary_path), str(path)], summary=payload)
