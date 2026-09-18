from __future__ import annotations
from typing import Any
from .base import ModuleResult
from .utils import write_text, write_json, ensure_dir, FIB

class SEOEngine:
    name = "seo_engine"
    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        out_dir = f"{run_folder}/artifacts/{self.name}"
        ensure_dir(out_dir)
        clusters = [f"{topic} basics", f"{topic} templates", f"{topic} automation"]
        briefs = [{"id": i, "title": f"{topic}: Guide #{i}", "outline": ["3 points","6 steps","9 checklist"]} for i in range(1,10)]
        write_json(f"{out_dir}/keyword_clusters.json", {"clusters": clusters})
        write_json(f"{out_dir}/briefs.json", briefs)
        md = "# SEO Briefs (9)\n\n" + "\n".join([f"- {b['title']}" for b in briefs])
        md += "\n\n## Refresh cadence (Fib)\n" + "\n".join([f"- Day {d}: refresh top pages" for d in FIB[:6]])
        write_text(f"{out_dir}/SEO_BRIEFS.md", md)
        return ModuleResult(name=self.name, artifacts=[f"{out_dir}/SEO_BRIEFS.md", f"{out_dir}/keyword_clusters.json", f"{out_dir}/briefs.json"], summary={"briefs": 9})
