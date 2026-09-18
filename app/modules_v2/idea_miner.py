from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from app.modules.base import BaseModule
from .base import ModuleResult


class IdeaMiner(BaseModule):
    name = "idea_miner"

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
        out_dir = Path(merged.get("output_dir") or run_folder) / "idea_miner"
        out_dir.mkdir(parents=True, exist_ok=True)

        audience = str(merged.get("audience") or "digital creators")
        ideas = [
            {
                "idea": f"{topic} Starter Playbook",
                "format": "guide + checklist",
                "price_hint": "$19",
                "best_workflow": "vault_to_money_pack",
            },
            {
                "idea": f"{topic} Weekly Signals Newsletter",
                "format": "membership content",
                "price_hint": "$12/mo",
                "best_workflow": "vault_to_membership_pack",
            },
            {
                "idea": f"{topic} Launch Sprint Kit",
                "format": "template bundle + scripts",
                "price_hint": "$29",
                "best_workflow": "vault_to_money_publish",
            },
        ]

        payload = {
            "topic": topic,
            "status": "ok",
            "audience": audience,
            "ideas": ideas,
            "workflow_suggestions": sorted({i["best_workflow"] for i in ideas}),
            "generated_at": datetime.utcnow().isoformat(),
        }
        summary_path = out_dir / f"idea_miner_{int(time.time())}.json"
        summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return ModuleResult(name=self.name, artifacts=[str(summary_path)], summary=payload)
