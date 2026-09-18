from __future__ import annotations
from typing import Any
from .base import ModuleResult
from .utils import write_text, write_json, ensure_dir

class LocalizationEngine:
    name = "localization_engine"
    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        out_dir = f"{run_folder}/artifacts/{self.name}"
        ensure_dir(out_dir)
        langs = constraints.get("languages") or ["es","fr","de"]
        arts=[]
        for lang in langs:
            p = f"{out_dir}/listing_{lang}.md"
            write_text(p, f"# Listing Copy ({lang})\n\nTitle: {topic}\n\nSubtitle: (translate)\n\nBullets (6): (translate)\n\nTags (9): (translate)\n\nDisclosure: disclose affiliate links if used.\n")
            arts.append(p)
        write_json(f"{out_dir}/languages.json", {"languages": langs})
        return ModuleResult(name=self.name, artifacts=arts+[f"{out_dir}/languages.json"], summary={"languages": langs})
