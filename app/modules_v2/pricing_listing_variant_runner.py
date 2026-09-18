from __future__ import annotations
from typing import Any
import os
import sqlite3

from .base import ModuleResult
from .utils import ensure_dir, write_text, write_json, slugify, FIB
from ..config import EV_DB_PATH
from .. import db


def _fetch_analytics_by_sku(sku: str | None = None, platform: str | None = None):
    conn = sqlite3.connect(EV_DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    q = "SELECT platform, sku, SUM(COALESCE(orders,0)) as orders, SUM(COALESCE(gross_cents,0)) as gross_cents, SUM(COALESCE(net_cents,0)) as net_cents, SUM(COALESCE(refunds,0)) as refunds, COUNT(*) as rows FROM analytics_rows"
    clauses = []
    params: list[Any] = []
    if sku:
        clauses.append("sku=?")
        params.append(sku)
    if platform:
        clauses.append("platform=?")
        params.append(platform)
    if clauses:
        q += " WHERE " + " AND ".join(clauses)
    q += " GROUP BY platform, sku ORDER BY net_cents DESC"
    cur.execute(q, tuple(params))
    out = [dict(r) for r in cur.fetchall()]
    conn.close()
    return out


def _price_ladder(base_cents: int) -> list[int]:
    # 3/6/9-aligned ladder around base: down, base, up
    # Keep cents rounded to 100.
    if base_cents <= 0:
        base_cents = 2900
    low = max(500, int(round(base_cents * 0.618 / 100.0)) * 100)
    mid = int(round(base_cents / 100.0)) * 100
    high = int(round(base_cents * 1.618 / 100.0)) * 100
    return [low, mid, high]


class PricingListingVariantRunner:
    """Unifies analytics → next experiments → listing variants.

    - Reads normalized analytics_rows from local SQLite.
    - Suggests the next 3 tests (pricing + titles).
    - Optionally enqueues tasks to build variants.

    Local-only. No external APIs.
    """

    name = "pricing_listing_variant_runner"

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

        target_skus = constraints.get("skus")  # optional list
        platform = constraints.get("platform")
        enqueue = bool(constraints.get("enqueue", False))

        # If no target skus provided, use top products in registry
        products = db.list_products(limit=int(constraints.get("max_products", 50)))
        if target_skus and isinstance(target_skus, list):
            products = [p for p in products if p.get("sku") in set(target_skus)]

        experiments = []
        enqueued = 0

        for p in products[: int(constraints.get("max_skus", 9))]:
            p_sku = p.get("sku")
            base_price = int(p.get("price_cents") or price_cents or 2900)
            ladder = _price_ladder(base_price)
            stats = _fetch_analytics_by_sku(p_sku, platform=platform)
            net = sum(int(r.get("net_cents") or 0) for r in stats) if stats else 0
            orders = sum(int(r.get("orders") or 0) for r in stats) if stats else 0

            # Next 3 tests: price, title hook, bundle mention
            exp = {
                "sku": p_sku,
                "title": p.get("title"),
                "current_price_cents": base_price,
                "observed_orders": orders,
                "observed_net_cents": net,
                "price_tests_cents": ladder,
                "listing_title_variants": [
                    f"{p.get('title')} — Quickstart (369)",
                    f"{p.get('title')} — Complete System (Φ Bundle)",
                    f"{p.get('title')} — Templates + Checklists (Fib cadence)",
                ],
                "cadence_days": FIB[:5],
            }
            experiments.append(exp)

            if enqueue:
                # enqueue 3 pricing variants as separate SKUs
                for i, pc in enumerate(ladder, start=1):
                    v_sku = f"{p_sku}-P{i}"
                    v_topic = f"{p.get('title')} (Price Test {i})"
                    db.enqueue_task(
                        sku=v_sku,
                        topic=v_topic,
                        tier=p.get("tier") or tier,
                        price_cents=int(pc),
                        platforms=platforms,
                        constraints={
                            "modules": [
                                "marketplace_listing_optimizer",  # if present
                                "platform_packs",
                                "licensing_matrix_generator",
                            ],
                            "listing_title": exp["listing_title_variants"][i-1],
                            "variant_of": p_sku,
                            "price_test": True,
                        },
                    )
                    enqueued += 1

        report_lines = ["# Pricing + Listing Variant Runner", "", f"Topic: {topic}", ""]
        report_lines.append("## What this does")
        report_lines.append("- Reads normalized analytics from your local DB")
        report_lines.append("- Suggests next pricing + listing tests")
        report_lines.append("- Optional: enqueues variant builds into the local factory queue")
        report_lines.append("")

        for e in experiments:
            report_lines.append(f"## {e['sku']} — {e['title']}")
            report_lines.append(f"- Observed: {e['observed_orders']} orders • ${e['observed_net_cents']/100:.2f} net")
            report_lines.append(f"- Price ladder: {', '.join('$'+format(x/100, '.2f') for x in e['price_tests_cents'])}")
            report_lines.append("- Title variants:")
            for t in e["listing_title_variants"]:
                report_lines.append(f"  - {t}")
            report_lines.append(f"- Cadence: days {', '.join(str(d) for d in e['cadence_days'])}")
            report_lines.append("")

        report_lines.append("## Next-step plan (369)")
        report_lines.append("1) Run 3 tests (price + title) on your best SKU")
        report_lines.append("2) Keep winner, roll forward")
        report_lines.append("3) Add social proof + bundles")

        report_path = os.path.join(out_dir, "EXPERIMENTS.md")
        json_path = os.path.join(out_dir, "experiments.json")
        write_text(report_path, "\n".join(report_lines))
        write_json(json_path, {"topic": topic, "platform": platform, "experiments": experiments, "enqueued": enqueued})

        return ModuleResult(self.name, [report_path, json_path], {"ok": True, "skus": len(experiments), "enqueued": enqueued})
