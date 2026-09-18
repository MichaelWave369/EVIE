from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from app.modules.base import BaseModule
from .base import ModuleResult


class ShortFormPack(BaseModule):
    name = "short_form_pack"

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
        out_dir = Path(merged.get("output_dir") or run_folder) / "short_form_pack"
        out_dir.mkdir(parents=True, exist_ok=True)
        n = max(3, min(12, int(merged.get("clips") or 6)))
        clips = []
        for i in range(1, n + 1):
            clips.append(
                {
                    "clip": i,
                    "hook": f"{topic}: one tactic in 15 seconds ({i})",
                    "tiktok_script": f"Hook -> one proof -> CTA for {topic}.",
                    "instagram_reel_caption": f"Quick {topic} win #{i}",
                    "youtube_shorts_caption": f"{topic} quick tip #{i}",
                }
            )
        payload = {"topic": topic, "status": "ok", "short_form_pack": clips, "generated_at": datetime.utcnow().isoformat()}
        p = out_dir / f"short_form_pack_{int(time.time())}.json"
        p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return ModuleResult(name=self.name, artifacts=[str(p)], summary=payload)
