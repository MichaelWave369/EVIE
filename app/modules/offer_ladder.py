from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import datetime, json
from app.modules.base import ModuleResult
from app.rag.llm import LLM
from app.settings import settings
from app.export.packager import write_text


class OfferLadderModule:
    name = "offer_ladder"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        llm = LLM.from_settings()
        niche = constraints.get("niche", "general")
        prompt = f"""Create a 369/Φ offer ladder for passive income.

Topic: {topic}
Niche: {niche}

Must include:
- 3 tiers (Entry/Core/Premium)
- 3 packaging styles (Starter/Builder/Operator)
- 3 delivery modes (Download/Video/Subscription)
- Recommended price ranges
- Bundling logic (Φ ratio) and Fibonacci release roadmap
"""
        text = llm.chat([{"role":"user","content":prompt}])
        out_dir = Path(settings.data_dir) / "artifacts" / "offer_ladder"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        path = out_dir / f"offer_ladder__{ts}.md"
        write_text(path, text)
        return ModuleResult([str(path)], {"module": self.name, "topic": topic, "niche": niche})
