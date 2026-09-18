from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from app.modules.base import BaseModule
from .base import ModuleResult


class HooksGenerator(BaseModule):
    name = "hooks_generator"

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

        script = str(merged.get("script") or "")
        if not script:
            script_path = str(merged.get("script_path") or "")
            if script_path and Path(script_path).exists():
                script = Path(script_path).read_text(encoding="utf-8", errors="ignore")
        if not script:
            for p in merged.get("artifact_paths") or []:
                if str(p).lower().endswith(".md") and Path(p).exists():
                    script = Path(p).read_text(encoding="utf-8", errors="ignore")
                    break

        hooks = self._build_hooks(topic, script)
        payload = {
            "topic": topic,
            "hooks": hooks,
            "categories": {
                "educational": hooks[:3],
                "controversial": hooks[3:6],
                "curiosity": hooks[6:9],
            },
            "generated_at": datetime.utcnow().isoformat(),
        }

        out_dir = Path(merged.get("output_dir") or "data/artifacts/hooks")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"hooks_{re.sub(r'[^a-z0-9]+', '_', topic.lower())[:40]}.json"
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        return ModuleResult(name=self.name, artifacts=[str(out_path)], summary=payload)

    def _build_hooks(self, topic: str, script: str) -> list[str]:
        seeds = []
        if script:
            chunks = re.split(r"[\n\.!?]", script)
            seeds = [c.strip() for c in chunks if len(c.strip()) > 20][:6]
        if not seeds:
            seeds = [
                f"Most people misunderstand {topic} — here's what actually works.",
                f"If you're stuck with {topic}, this is the reset you need.",
                f"The 10-minute {topic} shift that changes everything.",
            ]

        templates = [
            "Stop scrolling: {line}",
            "Hard truth: {line}",
            "Nobody tells you this about {topic}: {line}",
            "This one {topic} mistake costs you momentum.",
            "Try this before your next {topic} session.",
            "{topic} in plain English: {line}",
            "You can feel the difference in 7 days: {line}",
            "The framework I wish I had sooner for {topic}.",
            "Question: are you overcomplicating {topic}?",
        ]
        out = []
        for i, t in enumerate(templates):
            line = seeds[i % len(seeds)] if seeds else topic
            out.append(t.format(topic=topic, line=line))
        return out[:9]
