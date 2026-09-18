from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import datetime
from app.modules.base import ModuleResult
from app.rag.llm import LLM
from app.settings import settings
from app.export.packager import write_text

class NewsletterModule:
    name = "newsletter"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        llm = LLM.from_settings()
        tone = constraints.get("tone", "helpful, direct, slightly mythic")
        length = constraints.get("length", "800-1200 words")
        include_offer = constraints.get("include_offer", True)

        prompt = f"""Write a newsletter issue in markdown.

Topic: {topic}
Tone: {tone}
Length: {length}
Structure:
- Subject lines (8)
- Opening story (short)
- 3 actionable lessons
- A checklist
- A 'Next 3 Moves' section
- If include_offer={include_offer}, add a soft offer for an ebook/course/template
- Enforce 369 / Φ / Fibonacci alignment:
  - 3 sections: Insight / Story / Action
  - 6 bullets max, 9 if needed
  - Close with 1-2-3-5-8 'next steps'
"""
        text = llm.chat([{"role":"user","content":prompt}])
        out_dir = Path(settings.data_dir) / "artifacts" / "newsletter"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        md_path = out_dir / f"newsletter__{ts}.md"
        write_text(md_path, text)

        return ModuleResult(artifact_paths=[str(md_path)], metadata={"topic": topic, "module": self.name})
