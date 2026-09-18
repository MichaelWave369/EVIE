from __future__ import annotations
from typing import Any
import re
from .base import ModuleResult
from .utils import ensure_dir, write_text, write_json, now_iso, phi_split
from .. import db

def _tokens(s: str) -> set[str]:
    s = re.sub(r"[^a-z0-9 ]+", " ", s.lower())
    toks = [t for t in s.split() if len(t) > 2]
    return set(toks)

def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0

class BundleUpsellEngine:
    """Turn your catalog into a compounding ecosystem: cross-sells, order bumps, Phi bundles."""
    name = "bundle_upsell_engine"

    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        out_dir = f"{run_folder}/artifacts/{self.name}"
        ensure_dir(out_dir)

        products = db.list_products(limit=int(constraints.get("catalog_limit") or 200))
        # build similarity graph
        items = []
        for p in products:
            title = p.get("title","")
            items.append({**p, "tokens": _tokens(title)})

        bundles = []
        order_bumps = []
        cross_sells = []

        for i,a in enumerate(items):
            for b in items[i+1:]:
                sim = _jaccard(a["tokens"], b["tokens"])
                if sim >= 0.18:
                    cross_sells.append({"a": a["sku"], "b": b["sku"], "score": round(sim,3)})
        cross_sells.sort(key=lambda x: x["score"], reverse=True)

        # suggest bundles: top related pairs grouped by topic tokens
        top_pairs = cross_sells[:27]  # 3x9
        seen = set()
        for pair in top_pairs:
            key = tuple(sorted([pair["a"], pair["b"]]))
            if key in seen:
                continue
            seen.add(key)
            pa = next((x for x in products if x["sku"]==pair["a"]), None)
            pb = next((x for x in products if x["sku"]==pair["b"]), None)
            if not pa or not pb:
                continue
            sum_cents = int(pa.get("price_cents",0)) + int(pb.get("price_cents",0))
            # Phi discount: buyer pays ~61.8% of total
            bundle_price = max(900, int(sum_cents * 0.618))
            bundles.append({
                "bundle_sku": f"BUNDLE-{pa['sku']}-{pb['sku']}",
                "items": [pa["sku"], pb["sku"]],
                "sum_price_cents": sum_cents,
                "phi_bundle_price_cents": bundle_price,
                "discount_pct": round(100*(1 - bundle_price/max(1,sum_cents)), 1),
            })

        # order bump suggestion: split current price by phi
        major, minor = phi_split(max(900, price_cents))
        order_bumps.append({
            "core_sku": sku,
            "bump_price_cents": minor,
            "bump_idea": "Add a 'Quickstart + Checklist Pack' as an order bump.",
        })

        md = [f"# Bundle + Upsell Engine — {topic}", ""]
        md += ["## Phi Bundle Strategy", "- Build pairs/triples that share keywords.", "- Price bundles at ~61.8% of total.", ""]
        md += ["## Suggested bundles (top 9)", ""]
        for b in bundles[:9]:
            md.append(f"- **{b['bundle_sku']}** = {b['items']} → ${b['phi_bundle_price_cents']/100:.2f} (discount ~{b['discount_pct']}%)")
        md += ["", "## Cross-sell pairs (top 9)", ""]
        for p in cross_sells[:9]:
            md.append(f"- {p['a']} ↔ {p['b']} (score {p['score']})")
        md += ["", "## Order bump", ""]
        for ob in order_bumps:
            md.append(f"- Core {ob['core_sku']}: bump ${ob['bump_price_cents']/100:.2f} — {ob['bump_idea']}")
        md += ["", "## Cross-sell page block (copy/paste)", "", "```", "Complete your collection:", "- Add the companion pack for a Phi discount.", "```", ""]
        md_path = f"{out_dir}/UPSELLS.md"
        write_text(md_path, "\n".join(md))

        data = {"generated_at": now_iso(), "sku": sku, "bundles": bundles, "cross_sells": cross_sells[:100], "order_bumps": order_bumps}
        json_path = f"{out_dir}/upsells.json"
        write_json(json_path, data)
        return ModuleResult(name=self.name, artifacts=[md_path, json_path], summary={"bundles": len(bundles), "pairs": len(cross_sells)})
