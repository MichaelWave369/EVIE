from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import datetime, json
from app.modules.base import ModuleResult
from app.rag.llm import LLM
from app.settings import settings
from app.export.packager import write_text

class PrintOnDemandModule:
    name = "pod"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        llm = LLM.from_settings()
        audience = constraints.get("audience", "builders/operators")
        style = constraints.get("style", "clean, symbolic, 369/phi vibes")

        prompt = f"""Design a print-on-demand mini-collection (text only; no images).

Theme: {topic}
Audience: {audience}
Style: {style}

Output:
- 12 slogan/phrase options (short)
- 12 longer back-print statements
- 9 icon/concept ideas (simple shapes)
- Product types to use (shirt/hoodie/mug/poster/etc.)
- Listing titles + descriptions (5)
- Keyword list (30)
- Enforce 369 / Φ / Fibonacci alignment:
  - 3 design themes, 6 SKU variants, 9 slogans
"""
        text = llm.chat([{"role":"user","content":prompt}])
        out_dir = Path(settings.data_dir) / "artifacts" / "pod"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        md_path = out_dir / f"pod__{ts}.md"
        write_text(md_path, text)
        return ModuleResult(artifact_paths=[str(md_path)], metadata={"topic": topic, "module": self.name})
