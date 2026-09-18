from __future__ import annotations
from typing import Any
from .base import ModuleResult
from .utils import write_text, write_json, ensure_dir, slugify

class ProgrammaticSEOGenerator:
    name = "programmatic_seo_generator"
    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        out_dir = f"{run_folder}/artifacts/{self.name}"
        pages_dir = f"{out_dir}/pages"
        ensure_dir(pages_dir)
        max_pages = int(constraints.get("max_pages", 9))
        pages=[]
        for i in range(1, max_pages+1):
            title = f"{topic} — Evergreen Page {i}"
            slug = slugify(title)
            body = f"""# {title}

## 3 Pillars
- Create
- Distribute
- Compound

## 6 Steps
1) Define offer
2) Build bundle
3) Publish pack
4) Follow up
5) Measure
6) Iterate

## 9 Checklist items
1) Title
2) Subtitle
3) Description
4) Keywords
5) Visuals
6) License
7) FAQ
8) Update plan
9) Support plan
"""
            path = f"{pages_dir}/{slug}.md"
            write_text(path, body)
            pages.append({"title": title, "slug": slug, "path": path})
        write_json(f"{out_dir}/sitemap.json", pages)
        return ModuleResult(name=self.name, artifacts=[p["path"] for p in pages] + [f"{out_dir}/sitemap.json"], summary={"pages": len(pages)})
