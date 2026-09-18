from __future__ import annotations
from typing import Any
from .base import ModuleResult
from .utils import write_text, write_json, ensure_dir

class PlatformPacks:
    name = "platform_packs"
    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        out_dir = f"{run_folder}/artifacts/{self.name}"
        ensure_dir(out_dir)
        use = platforms or ["gumroad","etsy"]
        arts=[]
        for p in use:
            write_text(f"{out_dir}/{p}_CHECKLIST.md", f"# {p.upper()} Pack — {topic}\n\n## 3/6/9 Checklist\n- Create\n- Distribute\n- Compound\n")
            write_json(f"{out_dir}/{p}_FIELDS.json", {"sku": sku, "title": topic, "tier": tier, "price_cents": price_cents})
            arts += [f"{out_dir}/{p}_CHECKLIST.md", f"{out_dir}/{p}_FIELDS.json"]
        return ModuleResult(name=self.name, artifacts=arts, summary={"platforms": use})
