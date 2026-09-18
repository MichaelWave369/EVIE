from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import datetime, json

from app.modules.base import ModuleResult
from app.settings import settings
from app.export.packager import write_text
from app.rag.llm import LLM

FIB = [1,2,3,5,8,13]
def _fallback(topic: str, constraints: Dict[str, Any]) -> str:
    niche = constraints.get("niche", "general")
    fmt = constraints.get("format", "Notion + Obsidian + PDF")
    return f"""# Template Pack — {topic}

**Niche:** {niche}
**Formats:** {fmt}

## 369 Structure
### 3 Core Templates
1. Capture (Inbox)
2. Build (Project)
3. Ship (Release)

### 6 Supporting Templates
- Weekly Planner (Fib cadence)
- Checklist Library (1–2–3–5–8 steps)
- KPI Tracker (Φ 61.8/38.2)
- Asset Registry
- Customer Q&A Vault
- Launch Calendar

### 9 Automation Hooks (local-only)
1. Ingest notes → tag (Domain/Phase/State/Lens)
2. Generate outline
3. Generate draft
4. Package bundle
5. Create listing copy
6. Create email sequence
7. Create video script
8. Create social threads
9. Summarize analytics weekly

## Files to include in your pack
- templates/notion/ (JSON or markdown export notes)
- templates/obsidian/ (markdown vault structure)
- templates/pdf/ (printable pages)
- README.md (how to use)
- LICENSE.md (personal-use + commercial terms)

> Disclaimer: This is educational. Review for compliance and accuracy before selling.
"""


class TemplatePacksModule:
    name = "templates"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        llm = LLM.from_settings()
        niche = constraints.get("niche", "business + creators")
        target = constraints.get("target", "downloadable pack (zip)")
        prompt = f"""Create a *sellable* digital template pack.

Topic: {topic}
Niche: {niche}
Target: {target}

Must align to 369 / Φ / Fibonacci:
- 3 core templates
- 6 supporting templates
- 9 'automation hooks'
- Include a Fibonacci step ladder (1,2,3,5,8) inside at least 2 templates
- Include a Φ ratio KPI tracker (61.8/38.2 split)

Deliverables:
- README.md describing templates + use-cases
- TEMPLATE_INDEX.md listing each template and fields
- 3 sample templates as markdown tables (Capture, Build, Ship)
- A short license suggestion (personal / commercial)
- Simple listing copy: title, subtitle, 5 bullets, keywords
"""

        text = llm.chat([{"role":"user","content":prompt}])
        if settings.llm_backend.lower().strip() == "none":
            text = _fallback(topic, constraints)

        out_dir = Path(settings.data_dir) / "artifacts" / "templates"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        path = out_dir / f"templates__{ts}.md"
        write_text(path, text)

        # also emit a machine-readable manifest
        manifest = {
            "module": self.name,
            "topic": topic,
            "niche": niche,
            "created_at": datetime.datetime.utcnow().isoformat(),
            "alignment": {"pillars": 3, "loops": 6, "bots": 9, "fib": [1,2,3,5,8]}
        }
        mpath = out_dir / f"templates__{ts}.json"
        mpath.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        return ModuleResult(artifact_paths=[str(path), str(mpath)], metadata=manifest)
