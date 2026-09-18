from __future__ import annotations
from typing import Any
from .base import ModuleResult
from .utils import ensure_dir, write_text, now_iso

class SocialPosts:
    name = "social_posts"
    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        out_dir = f"{run_folder}/artifacts/{self.name}"
        ensure_dir(out_dir)
        md = f"""# Social Post Pack — {topic}

## 3 short posts
1) Hook + insight + CTA
2) Mistake + fix + CTA
3) Checklist + CTA

## 6 thread bullets
- 
- 
- 
- 
- 
- 

## 9 hooks
1) I used to think...
2) The hard truth is...
3) Here’s the checklist...
4) Stop doing this...
5) Do this instead...
6) If you only do one thing...
7) This saved me hours...
8) Most people miss this...
9) The simplest fix is...
"""
        path = f"{out_dir}/SOCIAL_POSTS.md"
        write_text(path, md)
        return ModuleResult(name=self.name, artifacts=[path], summary={"generated_at": now_iso()})
