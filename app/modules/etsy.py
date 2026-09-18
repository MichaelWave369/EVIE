from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import datetime, json
from app.modules.base import ModuleResult
from app.rag.llm import LLM
from app.settings import settings
from app.export.packager import write_text

class EtsyModule:
    name = "etsy"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        llm = LLM.from_settings()
        product_type = constraints.get("product_type", "digital template pack")
        niche = constraints.get("niche", "small business / operators")
        files = constraints.get("files", ["checklist", "planner", "SOP", "worksheet"])

        prompt = f"""Design an Etsy digital product.

Topic: {topic}
Product type: {product_type}
Niche: {niche}
Include:
- Product concept + what problem it solves
- File list: {files}
- 10 listing title options
- SEO keyword list (30)
- Listing description (with sections + FAQ)
- Simple usage instructions
- 5 mockup ideas (text-only)
- Enforce 369 / Φ / Fibonacci alignment:
  - Provide 3 product concepts, 6 variations, 9 listing keywords
  - Pricing ladder in Fibonacci increments when reasonable
"""
        text = llm.chat([{"role":"user","content":prompt}])
        out_dir = Path(settings.data_dir) / "artifacts" / "etsy"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        md_path = out_dir / f"etsy__{ts}.md"
        write_text(md_path, text)

        return ModuleResult(artifact_paths=[str(md_path)], metadata={"topic": topic, "module": self.name})
