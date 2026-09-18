from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import datetime, json

from app.modules.base import ModuleResult
from app.settings import settings
from app.export.packager import write_text
from app.rag.llm import LLM

def _fallback(topic: str) -> str:
    return f"""# Paid Community Playbook — {topic}

## Format
- 12-week program (Fib expansion)
- Weekly prompts + challenges + worksheets
- Onboarding + rules

## 369
- 3 weekly rituals
- 6 challenge tracks
- 9 community prompts

> Disclaimer: Community guidelines required. Moderate responsibly.
"""


class CommunityPlaybookModule:
    name = "community"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        llm = LLM.from_settings()
        duration = constraints.get("duration", "12 weeks")
        prompt = f"""Create a paid community playbook.

Theme: {topic}
Duration: {duration}

Must align to 369 / Φ / Fibonacci:
- 3 rituals (daily/weekly)
- 6 tracks (beginner -> advanced)
- 9 prompts per week (discussion + action)
- Provide a 4-week mini version and 12-week full version
- Include onboarding email + rules + moderation checklist
- Include pricing ladder (3 tiers) + benefits
"""
        text = llm.chat([{"role":"user","content":prompt}])
        if settings.llm_backend.lower().strip() == "none":
            text = _fallback(topic)

        out_dir = Path(settings.data_dir) / "artifacts" / "community"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        md = out_dir / f"community__{ts}.md"
        write_text(md, text)
        meta = {"module": self.name, "topic": topic, "duration": duration, "created_at": datetime.datetime.utcnow().isoformat()}
        j = out_dir / f"community__{ts}.json"
        j.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return ModuleResult(artifact_paths=[str(md), str(j)], metadata=meta)
