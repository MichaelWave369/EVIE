from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import datetime
from app.modules.base import ModuleResult
from app.rag.llm import LLM
from app.settings import settings
from app.export.packager import write_text

class StockMediaModule:
    name = "stock"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        llm = LLM.from_settings()
        media_type = constraints.get("media_type", "video")
        count = int(constraints.get("count", 25))

        prompt = f"""Create a stock {media_type} production plan.

Theme: {topic}
Deliverables count: {count}

Include:
- Shot list (count items) with scene description + framing + duration
- Metadata for each: title, description, 10 keywords
- Batch naming convention
- Simple production checklist (gear, lighting, releases)
- Enforce 369 / Φ / Fibonacci alignment:
  - 3 packs, 6 scenes each, 9 keyword tags per pack
"""
        text = llm.chat([{"role":"user","content":prompt}])
        out_dir = Path(settings.data_dir) / "artifacts" / "stock"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        md_path = out_dir / f"stock__{ts}.md"
        write_text(md_path, text)
        return ModuleResult(artifact_paths=[str(md_path)], metadata={"topic": topic, "module": self.name})
