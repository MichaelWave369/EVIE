from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import datetime, json
from app.modules.base import ModuleResult
from app.rag.llm import LLM
from app.settings import settings
from app.export.packager import write_text


class ConversionPackagerModule:
    name = "conversion_packager"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        llm = LLM.from_settings()
        product = constraints.get("product_name", f"{topic} Bundle")
        price = constraints.get("price", "$29-$99")
        prompt = f"""Create a conversion pack for a digital product.

Product: {product}
Topic: {topic}
Target price: {price}

Deliver:
- Landing page copy (headline, bullets, sections, CTA)
- 5-email sequence using Fibonacci cadence (1,2,3,5,8 style)
- FAQ (9 questions)
- 3 ad scripts + 8 short hooks
- Compliance: include affiliate disclosure placeholder and avoid guaranteed claims
"""
        text = llm.chat([{"role":"user","content":prompt}])
        out_dir = Path(settings.data_dir) / "artifacts" / "conversion_packager"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        path = out_dir / f"conversion_pack__{ts}.md"
        write_text(path, text)
        return ModuleResult([str(path)], {"module": self.name, "topic": topic, "product": product})
