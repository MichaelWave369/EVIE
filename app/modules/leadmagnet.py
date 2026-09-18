from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import datetime, json

from app.modules.base import ModuleResult
from app.settings import settings
from app.export.packager import write_text
from app.rag.llm import LLM

def _fallback(topic: str) -> str:
    return f"""# Lead Magnet Funnel — {topic}

## Assets
- Lead magnet PDF outline (3 parts)
- Landing page copy (headline, bullets, FAQ)
- 5-email sequence (Fib cadence: day 1,2,3,5,8)

## 369
- 3 promises
- 6 proof points
- 9 objections handled

> Disclaimer: Review for compliance and claims.
"""


class LeadMagnetModule:
    name = "leadmagnet"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        llm = LLM.from_settings()
        goal = constraints.get("goal", "collect emails, upsell to core offer")
        prompt = f"""Build a lead magnet funnel package.

Topic: {topic}
Goal: {goal}

Must align to 369 / Φ / Fibonacci:
- Lead magnet: 3 parts, 6 sections, 9 checkboxes
- Landing page: Φ structure (61.8% value, 38.2% CTA)
- Email sequence: 5 emails scheduled on days 1,2,3,5,8

Deliverables:
- lead_magnet_outline.md
- landing_page_copy.md
- email_sequence.md (5 emails)
- disclaimer + disclosure placeholders
"""
        text = llm.chat([{"role":"user","content":prompt}])
        if settings.llm_backend.lower().strip() == "none":
            text = _fallback(topic)

        out_dir = Path(settings.data_dir) / "artifacts" / "leadmagnet"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        md = out_dir / f"leadmagnet__{ts}.md"
        write_text(md, text)
        meta = {"module": self.name, "topic": topic, "goal": goal, "created_at": datetime.datetime.utcnow().isoformat()}
        j = out_dir / f"leadmagnet__{ts}.json"
        j.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return ModuleResult(artifact_paths=[str(md), str(j)], metadata=meta)
