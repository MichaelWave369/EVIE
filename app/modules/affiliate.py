from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import datetime
from app.modules.base import ModuleResult
from app.rag.llm import LLM
from app.settings import settings
from app.export.packager import write_text

class AffiliateModule:
    name = "affiliate"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        llm = LLM.from_settings()
        niche = constraints.get("niche", "tools + workflows")
        disclosure = constraints.get("disclosure", True)

        prompt = f"""Create an affiliate-ready article draft (markdown).

Topic: {topic}
Niche: {niche}

Include:
- Clear intro + who it's for
- 7-12 recommendations with pros/cons + 'best for'
- Comparison table
- Buyer guide + FAQ
- Suggested affiliate link placement markers like [LINK: product-name]
- If disclosure={disclosure}, include an affiliate disclosure block at the top
- Enforce 369 / Φ / Fibonacci alignment:
  - 3 angles, 6 talking points, 9 SEO keywords
  - CTA placed at Φ point (~62% through)
"""
        text = llm.chat([{"role":"user","content":prompt}])
        out_dir = Path(settings.data_dir) / "artifacts" / "affiliate"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        md_path = out_dir / f"affiliate__{ts}.md"
        write_text(md_path, text)
        return ModuleResult(artifact_paths=[str(md_path)], metadata={"topic": topic, "module": self.name})
