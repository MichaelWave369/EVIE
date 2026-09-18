from __future__ import annotations
from typing import Any
from .base import ModuleResult
from .utils import ensure_dir, write_text, now_iso

class LeadMagnetSnippet:
    name = "lead_magnet_snippet"
    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        out_dir = f"{run_folder}/artifacts/{self.name}"
        ensure_dir(out_dir)
        md = f"""# Lead Magnet Snippet — {topic}

## One-page checklist (369)
### 3 pillars
- 
- 
- 

### 6 steps
1) 
2) 
3) 
4) 
5) 
6) 

### 9 gotchas
1) 
2) 
3) 
4) 
5) 
6) 
7) 
8) 
9) 

**CTA:** Want the full kit + templates? Grab the bundle.
"""
        path = f"{out_dir}/LEAD_MAGNET.md"
        write_text(path, md)
        return ModuleResult(name=self.name, artifacts=[path], summary={"generated_at": now_iso()})
