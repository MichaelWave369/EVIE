from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from app.modules.base import BaseModule
from .base import ModuleResult


class ThreadBomber(BaseModule):
    name = "thread_bomber"

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
        out_dir = Path(merged.get("output_dir") or run_folder) / "thread_bomber"
        out_dir.mkdir(parents=True, exist_ok=True)

        wf = merged.get("workflow_step_metadata") or {}
        sales = (wf.get("sales_page_builder") or {}).get("v2_summary") or wf.get("sales_page_builder") or {}
        emails = (wf.get("email_sequence_builder") or {}).get("v2_summary") or wf.get("email_sequence_builder") or {}

        hooks = [
            f"Most creators overcomplicate {topic}.",
            f"Here is the {topic} playbook I wish I had sooner.",
            f"If you want repeatable results in {topic}, start here.",
        ]
        body = [
            f"{i+1}/ {h}" for i, h in enumerate(hooks)
        ] + [
            f"4/ Use this core promise: {(sales.get('sales_page') or {}).get('headline', f'Build a repeatable {topic} system.')}",
            "5/ Package one offer, one CTA, one channel at a time.",
            f"6/ CTA: {((emails.get('email_sequence') or [{}])[0]).get('cta', 'Reply for the template.')}",
        ]

        payload = {
            "topic": topic,
            "status": "ok",
            "x_thread": body,
            "linkedin_long_post": "\n".join(body),
            "generated_at": datetime.utcnow().isoformat(),
        }
        p = out_dir / f"thread_bomber_{int(time.time())}.json"
        p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return ModuleResult(name=self.name, artifacts=[str(p)], summary=payload)
