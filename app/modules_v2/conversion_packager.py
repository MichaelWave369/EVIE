from __future__ import annotations
from typing import Any
from .base import ModuleResult
from .utils import write_text, ensure_dir

class ConversionPackager:
    name = "conversion_packager"
    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        out_dir = f"{run_folder}/artifacts/{self.name}"
        ensure_dir(out_dir)
        write_text(f"{out_dir}/EMAIL_SEQUENCE.md", f"""# Email Sequence (Fib)

## Email 1 — Day 1
Subject: {topic} — welcome + quick win

## Email 2 — Day 2
Subject: {topic} — fix the common mistake

## Email 3 — Day 3
Subject: {topic} — example workflow

## Email 4 — Day 5
Subject: {topic} — the offer (no guarantees)

## Email 5 — Day 8
Subject: {topic} — bonus / bump
""")
        write_text(f"{out_dir}/FAQ.md", """# FAQ (9)
1) What is it?
2) Who is it for?
3) How do I use it?
4) What platforms does it support?
5) Does it guarantee results?
6) What about refunds?
7) Can I share/resell?
8) How are updates delivered?
9) Where do files live?
""")
        write_text(f"{out_dir}/SUPPORT_MACROS.md", """# Support Macros (9)
1) Install help
2) Download help
3) File not opening
4) How to customize
5) Refund request
6) License question
7) Update request
8) Compatibility
9) Other
""")
        return ModuleResult(name=self.name, artifacts=[f"{out_dir}/EMAIL_SEQUENCE.md", f"{out_dir}/FAQ.md", f"{out_dir}/SUPPORT_MACROS.md"], summary={"ok": True})
