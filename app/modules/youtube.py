from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import datetime
from app.modules.base import ModuleResult
from app.rag.llm import LLM
from app.settings import settings
from app.export.packager import write_text

class YouTubeModule:
    name = "youtube"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        llm = LLM.from_settings()
        format_ = constraints.get("format", "8-12 minute tutorial")
        hook = constraints.get("hook", "strong first 10 seconds")
        cta = constraints.get("cta", "subscribe + link to free download")

        prompt = f"""Write a YouTube script.

Topic: {topic}
Format: {format_}
Hook: {hook}
Include:
- Title options (5)
- Thumbnail text options (10)
- Script with timestamps
- On-screen notes
- Description + tags
- Enforce 369 / Φ / Fibonacci alignment:
  - Hook in first ~10% (Φ pacing)
  - 3-act structure, 6 segments, 9 key points
  - End with 1-2-3-5-8 action ladder
CTA: {cta}
"""

        text = llm.chat([{"role":"user","content":prompt}])
        out_dir = Path(settings.data_dir) / "artifacts" / "youtube"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        md_path = out_dir / f"youtube__{ts}.md"
        write_text(md_path, text)

        return ModuleResult(artifact_paths=[str(md_path)], metadata={"topic": topic, "module": self.name})
