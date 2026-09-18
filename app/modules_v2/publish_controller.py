from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.modules.base import BaseModule
from .base import ModuleResult


class PublishController(BaseModule):
    name = "publish_controller"

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
        auto_publish = bool(merged.get("auto_publish", False))
        dry_run = bool(merged.get("dry_run", False))
        publish_to_gumroad = bool(merged.get("publish_to_gumroad", True))
        publish_to_youtube = bool(merged.get("publish_to_youtube", True))

        decision = {
            "topic": topic,
            "status": "simulated" if dry_run else ("publish_enabled" if auto_publish else "export_only"),
            "auto_publish": auto_publish,
            "dry_run": dry_run,
            "allow_gumroad": bool(auto_publish and publish_to_gumroad),
            "allow_youtube": bool(auto_publish and publish_to_youtube),
            "publish_to_gumroad": publish_to_gumroad,
            "publish_to_youtube": publish_to_youtube,
            "generated_at": datetime.utcnow().isoformat(),
        }

        out_dir = Path(merged.get("output_dir") or run_folder)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "publish_controller.json"
        path.write_text(json.dumps(decision, indent=2), encoding="utf-8")
        return ModuleResult(name=self.name, artifacts=[str(path)], summary=decision)
