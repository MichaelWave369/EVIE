from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import datetime, json
from app.modules.base import ModuleResult
from app.rag.llm import LLM
from app.settings import settings
from app.export.packager import write_text


class RepurposerModule:
    """One idea -> 1/2/3/5/8 outputs (longform -> ebooks/scripts/posts/shorts)"""
    name = "repurposer"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        llm = LLM.from_settings()
        channel = constraints.get("channel", "youtube+blog+newsletter")
        style = constraints.get("style", "practical, systemized, 369-aligned")

        prompt = f"""Create a repurposing plan.

Topic: {topic}
Channels: {channel}
Style: {style}

Output:
- 1 cornerstone (outline)
- 2 ebooks (angles)
- 3 long videos (titles + hooks + beats)
- 5 blog posts (H1s + key bullets)
- 8 shorts (single ideas + CTA)
- 369 calendar: 3 days create, 6 distribute, 9 compound
"""
        plan = llm.chat([{"role":"user","content":prompt}])

        out_dir = Path(settings.data_dir) / "artifacts" / "repurposer"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        path = out_dir / f"repurpose_plan__{ts}.md"
        write_text(path, plan)
        return ModuleResult([str(path)], {"module": self.name, "topic": topic})
