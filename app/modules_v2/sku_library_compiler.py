from __future__ import annotations
from typing import Any
import os
import math

from .base import ModuleResult
from .utils import ensure_dir, write_text, write_json, slugify, phi_split
from .. import db


def _tokenize(s: str) -> set[str]:
    s = (s or "").lower()
    out = set()
    buf = []
    for ch in s:
        if ch.isalnum():
            buf.append(ch)
        else:
            if buf:
                out.add("".join(buf))
                buf = []
    if buf:
        out.add("".join(buf))
    return out


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


class SKULibraryCompiler:
    """Builds themed collections / bundles from your local product registry.

    Goal: turn a growing catalog into compounding bundles:
    - Complete collections
    - Starter packs
    - Tier-based stacks

    Local-only: reads SQLite products table and writes bundle plans + cross-sell pages.
    """

    name = "sku_library_compiler"

    def generate(
        self,
        *,
        topic: str,
        run_folder: str,
        sku: str,
        tier: str,
        price_cents: int,
        platforms: list[str],
        constraints: dict[str, Any],
    ) -> ModuleResult:
        tslug = slugify(topic)
        out_dir = os.path.join(run_folder, "artifacts", self.name, tslug)
        ensure_dir(out_dir)

        products = db.list_products(limit=int(constraints.get("max_products", 500)))
        if not products:
            # Not an error: the engine can still output a planning template.
            plan_path = os.path.join(out_dir, "COLLECTIONS.md")
            write_text(plan_path, "# SKU Library (empty)\n\nNo products found in local registry yet.\nRun /v1/flywheel/offer once, then re-run this module.\n")
            return ModuleResult(self.name, [plan_path], {"ok": True, "products": 0})

        # Build similarity clusters by title tokens
        tokens = {p["sku"]: _tokenize(p.get("title", "")) for p in products}

        # Choose up to 9 anchor products: most recently updated
        anchors = products[: min(9, len(products))]

        collections: list[dict[str, Any]] = []
        for a in anchors:
            a_sku = a["sku"]
            a_tok = tokens.get(a_sku, set())

            # Find complements
            scored = []
            for p in products:
                if p["sku"] == a_sku:
                    continue
                sim = _jaccard(a_tok, tokens.get(p["sku"], set()))
                scored.append((sim, p))
            scored.sort(key=lambda x: x[0], reverse=True)

            take = int(constraints.get("max_per_collection", 6))
            picks = [a] + [p for sim, p in scored[: max(0, take - 1)]]

            # Pricing: Φ discount against sum
            total = sum(int(p.get("price_cents") or 0) for p in picks)
            bundle_price = int(round(total * 0.618)) if total > 0 else 0

            coll = {
                "anchor_sku": a_sku,
                "title": f"{a.get('title','Collection')} — Complete Bundle",
                "skus": [p["sku"] for p in picks],
                "sum_price_cents": total,
                "bundle_price_cents": bundle_price,
                "phi_discount_ratio": 0.618,
            }
            collections.append(coll)

        # De-dup collections by sku list signature
        seen = set()
        uniq = []
        for c in collections:
            sig = tuple(c["skus"])
            if sig in seen:
                continue
            seen.add(sig)
            uniq.append(c)
        collections = uniq[: int(constraints.get("max_collections", 9))]

        # Write outputs
        md_lines = ["# SKU Library Collections (Φ bundles)", ""]
        for i, c in enumerate(collections, start=1):
            md_lines.append(f"## {i}. {c['title']}")
            md_lines.append(f"- Anchor: `{c['anchor_sku']}`")
            md_lines.append(f"- SKUs: {', '.join('`'+s+'`' for s in c['skus'])}")
            md_lines.append(f"- Sum: ${c['sum_price_cents']/100:.2f}")
            md_lines.append(f"- Φ bundle target: ${c['bundle_price_cents']/100:.2f} (~61.8%)")
            md_lines.append("")
            md_lines.append("### Cross-sell copy")
            md_lines.append("- If you like this, the complete bundle saves time + keeps everything coherent.")
            md_lines.append("- Includes templates, checklists, and compounding assets.")
            md_lines.append("")

        md_path = os.path.join(out_dir, "COLLECTIONS.md")
        json_path = os.path.join(out_dir, "collections.json")
        write_text(md_path, "\n".join(md_lines))
        write_json(json_path, {"topic": topic, "collections": collections})

        # Optional: enqueue bundle builds as tasks
        enq = bool(constraints.get("enqueue", False))
        enqueued = 0
        if enq:
            for c in collections:
                b_sku = f"BUNDLE-{c['anchor_sku']}"
                b_topic = c["title"]
                # Use tier "bundle" to make it distinct
                db.enqueue_task(
                    sku=b_sku,
                    topic=b_topic,
                    tier="bundle",
                    price_cents=int(c["bundle_price_cents"]),
                    platforms=platforms,
                    constraints={
                        "modules": [
                            "storefront_html_generator",
                            "platform_packs",
                            "licensing_matrix_generator",
                        ],
                        "bundle_skus": c["skus"],
                        "bundle_price_cents": int(c["bundle_price_cents"]),
                    },
                )
                enqueued += 1

        summary = {"ok": True, "products": len(products), "collections": len(collections), "enqueued": enqueued}
        return ModuleResult(self.name, [md_path, json_path], summary)
