from __future__ import annotations
from typing import Any
from .base import ModuleResult
from .utils import ensure_dir, write_text, now_iso

class YouTubeScript:
    name = "youtube_script"
    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        out_dir = f"{run_folder}/artifacts/{self.name}"
        ensure_dir(out_dir)
        md = f"""# YouTube Script — {topic} (8–12 min)

## 0:00 Hook (3 lines)
1) Problem
2) Promise (bounded)
3) Proof (demo mention)

## Structure (6 beats)
1) Before state
2) Framework (3/6/9)
3) Live example
4) Mistakes
5) Checklist
6) CTA

## Shorts cut list (9)
1) 10s hook
2) 20s framework
3) 15s mistake #1
4) 15s mistake #2
5) 15s mistake #3
6) 20s checklist
7) 10s CTA
8) 15s proof
9) 10s close
"""
        path = f"{out_dir}/YOUTUBE_SCRIPT.md"
        write_text(path, md)
        return ModuleResult(name=self.name, artifacts=[path], summary={"generated_at": now_iso()})
