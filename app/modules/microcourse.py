from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import datetime, json

from app.modules.base import ModuleResult
from app.settings import settings
from app.export.packager import write_text
from app.rag.llm import LLM

def _fallback(topic: str, constraints: Dict[str, Any]) -> str:
    return f"""# Micro-Course Blueprint — {topic}

## Φ Pacing
- 61.8% teaching
- 38.2% exercises + implementation

## 369 Syllabus
### Part 1 — Create (3 lessons)
1) Foundations
2) Setup
3) First win

### Part 2 — Distribute (3 lessons)
4) Publishing pipeline
5) Visibility + positioning
6) Repurposing

### Part 3 — Compound (3 lessons)
7) Offer ladder
8) Automation
9) Analytics + iteration

## Fibonacci Assignment Ladder
- 1: pick niche + outcome
- 2: create 2 assets
- 3: publish 3 posts
- 5: run 5 outreach actions
- 8: iterate 8 improvements

> Disclaimer: Educational only.
"""


class MicroCourseModule:
    name = "microcourse"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        llm = LLM.from_settings()
        length = constraints.get("length", "9 lessons (3x3)")
        platform = constraints.get("platform", "Teachable/Udemy/Gumroad (export)")
        prompt = f"""Design a micro-course that is *ready to record*.

Topic: {topic}
Length: {length}
Platform: {platform}

Must align to 369 / Φ / Fibonacci:
- 3 parts, 9 lessons
- lesson structure: Hook -> Teach -> Demo -> Exercise -> Checklist -> Next action
- Include a Fibonacci assignment ladder (1,2,3,5,8)
- Include a 'Course Assets' section: worksheets, templates, quiz prompts, community prompts
- Include sales page copy: headline, promise, bullets, FAQ, disclaimer

Output format: Markdown with clear headings.
"""
        text = llm.chat([{"role":"user","content":prompt}])
        if settings.llm_backend.lower().strip() == "none":
            text = _fallback(topic, constraints)

        out_dir = Path(settings.data_dir) / "artifacts" / "microcourse"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        md = out_dir / f"microcourse__{ts}.md"
        write_text(md, text)

        meta = {"module": self.name, "topic": topic, "length": length, "platform": platform, "created_at": datetime.datetime.utcnow().isoformat()}
        j = out_dir / f"microcourse__{ts}.json"
        j.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return ModuleResult(artifact_paths=[str(md), str(j)], metadata=meta)
