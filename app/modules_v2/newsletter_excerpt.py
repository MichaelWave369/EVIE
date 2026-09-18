from __future__ import annotations
from typing import Any
from .base import ModuleResult
from .utils import ensure_dir, write_text, now_iso

class NewsletterExcerpt:
    name = "newsletter_excerpt"
    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        out_dir = f"{run_folder}/artifacts/{self.name}"
        ensure_dir(out_dir)
        md = f"""# Newsletter Excerpt — {topic}

## Hook (3)
- The pain
- The shift
- The next step

## Body (6)
1) Context
2) Framework (3/6/9)
3) Example
4) Checklist
5) Common mistake
6) CTA

## CTA (9 words max)
Download the full kit + templates (local-only).
"""
        path = f"{out_dir}/NEWSLETTER.md"
        write_text(path, md)
        return ModuleResult(name=self.name, artifacts=[path], summary={"generated_at": now_iso()})
