from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import datetime, json
from app.modules.base import ModuleResult
from app.rag.llm import LLM
from app.settings import settings
from app.export.packager import write_text


class SupportMacrosModule:
    name = "support_macros"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        llm = LLM.from_settings()
        product = constraints.get("product_name", topic)
        prompt = f"""Create a support macro library for a product.

Product: {product}
Topic: {topic}

Include:
- 9 FAQ macros (short)
- 6 troubleshooting macros (step-by-step)
- 3 refund/chargeback macros (polite, firm)
- Include 'always local / privacy-first' language
"""
        text = llm.chat([{"role":"user","content":prompt}])
        out_dir = Path(settings.data_dir) / "artifacts" / "support_macros"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        path = out_dir / f"support_macros__{ts}.md"
        write_text(path, text)
        return ModuleResult([str(path)], {"module": self.name, "product": product})
