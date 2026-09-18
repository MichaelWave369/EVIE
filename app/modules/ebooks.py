from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import datetime
from app.modules.base import ModuleResult
from app.rag.llm import LLM
from app.settings import settings
from app.export.packager import write_text

class EbooksModule:
    name = "ebooks"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        # Generates a markdown manuscript draft (local LLM optional).
        llm = LLM.from_settings()
        audience = constraints.get("audience", "beginners")
        length = constraints.get("length", "short (25-40 pages)")
        style = constraints.get("style", "practical, step-by-step")

        prompt = f"""Create an ebook draft in markdown.

Topic: {topic}
Audience: {audience}
Target length: {length}
Style: {style}

Requirements:
- Enforce 369 / Φ / Fibonacci alignment:
  - 3 Parts (Create / Distribute / Compound)
  - 6 Sections minimum, 9 if possible
  - Use Fibonacci step ladders (1,2,3,5,8) for action plans
  - Use Φ ratio (~61.8% teaching / 38.2% practice)

- Strong title + subtitle
- Table of contents
- 6-10 chapters
- Each chapter: key ideas + checklist + 'next action'
- Include a short disclaimer section at end
"""

        text = llm.chat([{"role":"user","content":prompt}])
        out_dir = Path(settings.data_dir) / "artifacts" / "ebooks"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        md_path = out_dir / f"ebook__{ts}.md"
        write_text(md_path, text)

        return ModuleResult(artifact_paths=[str(md_path)], metadata={"topic": topic, "module": self.name})
