from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import datetime, json

from app.modules.base import ModuleResult
from app.settings import settings
from app.export.packager import write_text
from app.rag.llm import LLM

def _fallback(topic: str) -> str:
    return f"""# Licensing Pack — {topic}

## What this is
A licensing-ready asset bundle: templates + content + guidelines.

## Included
- Asset Manifest
- License Options (Personal, Commercial, Enterprise)
- Branding/usage guidelines
- Support boundaries (what you do / don’t provide)

## 369 Offer Ladder
- Tier 1 (Entry): Personal use
- Tier 2 (Core): Commercial use
- Tier 3 (Premium): Enterprise / redistribution

> Disclaimer: Not legal advice — have an attorney review your final license.
"""


class LicensingPackModule:
    name = "licensing"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        llm = LLM.from_settings()
        audience = constraints.get("audience", "creators, small businesses")
        prompt = f"""Create a licensing pack blueprint for a digital product.

Topic: {topic}
Audience: {audience}

Must include:
- Product Manifest (file list + purpose)
- 3-tier license ladder (personal, commercial, enterprise) aligned to 369
- Clear permissions + restrictions + attribution rules
- Refund/support boundaries
- A short 'Plain English' summary
- Listing copy: title, subtitle, bullets, keywords, pricing suggestion

Avoid: making legal guarantees. Add 'not legal advice' disclaimer.
"""
        text = llm.chat([{"role":"user","content":prompt}])
        if settings.llm_backend.lower().strip() == "none":
            text = _fallback(topic)

        out_dir = Path(settings.data_dir) / "artifacts" / "licensing"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        md = out_dir / f"licensing__{ts}.md"
        write_text(md, text)
        meta = {"module": self.name, "topic": topic, "audience": audience, "created_at": datetime.datetime.utcnow().isoformat()}
        j = out_dir / f"licensing__{ts}.json"
        j.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return ModuleResult(artifact_paths=[str(md), str(j)], metadata=meta)
