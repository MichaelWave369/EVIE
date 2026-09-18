from __future__ import annotations
from typing import Any
from .base import ModuleResult
from .utils import write_text, ensure_dir, FIB

class FunnelEngine:
    name = "funnel_engine"
    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        out_dir = f"{run_folder}/artifacts/{self.name}"
        ensure_dir(out_dir)
        landing = f"""# Landing Page — {topic}

## Hook (3 lines)
1) What it is
2) Who it's for
3) What changes (no guarantees)

## What you get (6 bullets)
- 369-structured guide
- Templates + checklists
- Email follow-up sequence
- SEO plan + page templates
- Support macros + refund flow
- Versioned updates + provenance stamp

## FAQ (9 quick answers)
1) Is this cloud? No — local-first.
2) Do I need code? No, but you can extend it.
3) What platforms? {", ".join(platforms)}
4) What if I don't publish? You can still build the library.
5) Any guarantees? No — you control execution.
6) Is it safe? Includes guardrails + disclosures.
7) Can I resell? Depends on license tier.
8) Updates? Versioned bundles.
9) Support? Macros included.

## Fib Follow-up cadence
""" + "\n".join([f"- Day {d}: message" for d in FIB[:6]]) + "\n"
        write_text(f"{out_dir}/LANDING_PAGE.md", landing)
        write_text(f"{out_dir}/ORDER_BUMP.md", "# Order Bump\n- Extra template pack\n- Extra 9 thumbnails\n- Extra 9 SEO briefs\n")
        write_text(f"{out_dir}/UPSELL.md", "# Upsell (Premium)\n- Licensing tier\n- 21-variant personalization map\n- Full 369 SEO page batch\n")
        return ModuleResult(name=self.name, artifacts=[f"{out_dir}/LANDING_PAGE.md", f"{out_dir}/ORDER_BUMP.md", f"{out_dir}/UPSELL.md"], summary={"ok": True})
