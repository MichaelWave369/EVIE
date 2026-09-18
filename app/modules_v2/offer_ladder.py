from __future__ import annotations
from typing import Any
from .base import ModuleResult
from .utils import write_text, write_json, ensure_dir, three_six_nine_sections, now_iso

class OfferLadder:
    name = "offer_ladder"
    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        out_dir = f"{run_folder}/artifacts/{self.name}"
        ensure_dir(out_dir)
        bullets3 = ["Create (assets)", "Distribute (reach)", "Compound (sales + reuse)"]
        bullets6 = [
            "Lead magnet mini-pack",
            "Core bundle (main product)",
            "Upsell add-on (templates/bonus)",
            "Premium licensing tier",
            "Support/FAQ macros",
            "Versioned updates"
        ]
        bullets9 = [
            "No hype, no guarantees",
            "Clear outcomes + boundaries",
            "369 structure everywhere",
            "Phi pacing (61.8/38.2)",
            "Fib followups (1/2/3/5/8)",
            "Tiered pricing (entry/core/premium)",
            "Bundles + order bump",
            "Evergreen updates",
            "Local-first provenance stamping"
        ]
        md = three_six_nine_sections(f"{topic} — Offer Ladder", bullets3, bullets6, bullets9)
        md += f"\n\n## Pricing suggestion (Phi)\n- Entry: ${max(9, int(price_cents/100*0.382))}\n- Core: ${int(price_cents/100)}\n- Premium: ${max(int(price_cents/100*3.4), 99)}\n"
        write_text(f"{out_dir}/OFFER_LADDER.md", md)
        write_json(f"{out_dir}/offer_ladder.json", {"sku": sku, "topic": topic, "generated_at": now_iso(), "entry_core_premium": ["entry","core","premium"]})
        return ModuleResult(name=self.name, artifacts=[f"{out_dir}/OFFER_LADDER.md", f"{out_dir}/offer_ladder.json"], summary={"ok": True})
