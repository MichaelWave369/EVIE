from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import datetime, json

from app.modules.base import ModuleResult
from app.rag.llm import LLM
from app.settings import settings
from app.export.packager import write_text
from app.flywheel.slug import slugify

class FunnelEngineModule:
    name = "funnel_engine"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        key = slugify(topic)
        out_dir = Path(settings.data_dir) / "artifacts" / "funnel_engine" / key
        out_dir.mkdir(parents=True, exist_ok=True)

        entry_price = constraints.get("entry_price", 19)
        core_price = constraints.get("core_price", 49)
        premium_price = constraints.get("premium_price", 199)
        niche = constraints.get("niche", "general")
        artifact_paths = constraints.get("artifact_paths") or []

        llm = LLM.from_settings()

        prompt = f"""Build a complete conversion funnel for a local-first digital product, aligned to 369/Φ/Fib.

Topic: {topic}
Niche: {niche}
Prices (suggested): Entry ${entry_price}, Core ${core_price}, Premium ${premium_price}

Requirements:
- Funnel map (Entry → Order bump → Core → Upsell → Premium → Subscription option)
- Landing page copy (sections in 3/6/9 structure)
- Checkout copy + risk reversal (no guarantees)
- Order bump offer (small, instant)
- Upsell offer (premium)
- Email sequences:
  - 1/2/3/5/8 day follow-ups (post-download)
  - 30/60/90 retention prompts
- Support boundary script to keep workload low
If artifacts exist, include a 'What files are included' section based on these paths:
{artifact_paths}

Return as Markdown with headings for each deliverable.
"""
        md = llm.chat([{"role":"user","content":prompt}])

        created=[]
        write_text(out_dir / "funnel_bundle.md", md)
        created.append(str(out_dir / "funnel_bundle.md"))

        # Split into convenience files (best-effort)
        parts = {
            "LANDING_PAGE.md": "Landing Page",
            "CHECKOUT_COPY.md": "Checkout",
            "EMAIL_SEQUENCE.md": "Email Sequences",
        }
        for fname, marker in parts.items():
            text = f"# {marker}\n\n" + md
            write_text(out_dir / fname, text)
            created.append(str(out_dir / fname))

        meta={"module": self.name, "topic": topic, "niche": niche, "prices": {"entry": entry_price, "core": core_price, "premium": premium_price}}
        return ModuleResult(created, meta)
