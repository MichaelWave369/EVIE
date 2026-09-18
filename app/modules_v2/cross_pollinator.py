from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from app.modules.base import BaseModule
from .base import ModuleResult


class CrossPollinator(BaseModule):
    name = "cross_pollinator"

    def _tokens(self, text: str) -> set[str]:
        return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if len(t) > 3}

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
        out_dir = Path(merged.get("output_dir") or run_folder) / "cross_pollinator"
        out_dir.mkdir(parents=True, exist_ok=True)

        context = str(merged.get("context") or "")
        notes = merged.get("vault_notes") or []
        if isinstance(notes, str):
            notes = [notes]
        sources = [topic, context, *[str(n) for n in notes[:20]]]
        token_sets = [self._tokens(s) for s in sources if s]

        overlap = set.intersection(*token_sets) if len(token_sets) >= 2 else (token_sets[0] if token_sets else set())
        bridges = [
            {
                "intersection_theme": tok,
                "product_angle": f"{tok} x {topic} implementation sprint",
                "asset_suggestion": "micro-course + checklist + newsletter issue",
            }
            for tok in sorted(list(overlap))[:8]
        ]
        if not bridges:
            bridges = [
                {
                    "intersection_theme": topic.lower(),
                    "product_angle": f"{topic} bundle with cross-domain positioning",
                    "asset_suggestion": "playbook + social launch pack",
                }
            ]

        payload = {
            "topic": topic,
            "status": "ok",
            "bridges": bridges,
            "generated_at": datetime.utcnow().isoformat(),
        }
        summary_path = out_dir / f"cross_pollinator_{int(time.time())}.json"
        summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return ModuleResult(name=self.name, artifacts=[str(summary_path)], summary=payload)
