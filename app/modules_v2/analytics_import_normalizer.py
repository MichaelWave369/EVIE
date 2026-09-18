from __future__ import annotations
from typing import Any
import csv, os, re, time, json
from .base import ModuleResult
from .utils import ensure_dir, write_text, write_json, now_iso
from .. import db

def _norm_col(c: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (c or "").strip().lower()).strip("_")

def _to_cents(v: str) -> int | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    s = s.replace(",", "")
    s = re.sub(r"[^0-9.\-]", "", s)
    if not s:
        return None
    try:
        return int(round(float(s) * 100))
    except Exception:
        return None

class AnalyticsImportNormalizer:
    """Normalize platform CSV exports (Gumroad/Etsy/KDP/Payhip/etc.) into one schema."""
    name = "analytics_import_normalizer"

    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        platform = (constraints.get("platform") or "unknown").lower()
        csv_path = constraints.get("csv_path")
        out_dir = f"{run_folder}/artifacts/{self.name}"
        ensure_dir(out_dir)

        if not csv_path or not os.path.exists(csv_path):
            md = """# Analytics Import Normalizer

Provide a local CSV path and platform name.

Example constraints:
- platform: gumroad | etsy | kdp | payhip
- csv_path: ./data/exports/gumroad_sales.csv

This module will output `normalized.csv` and a summary report.
"""
            write_text(f"{out_dir}/README.md", md)
            return ModuleResult(name=self.name, artifacts=[f"{out_dir}/README.md"], summary={"needs_csv": True})

        # read CSV
        with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # heuristics for common fields
        cols = { _norm_col(c): c for c in (rows[0].keys() if rows else []) }
        def pick(*cands):
            for c in cands:
                nc = _norm_col(c)
                if nc in cols:
                    return cols[nc]
            # fuzzy contains
            for nc, orig in cols.items():
                for cand in cands:
                    if _norm_col(cand) in nc:
                        return orig
            return None

        col_sku = pick("sku", "product_id", "product", "item", "title", "product_name")
        col_date = pick("date", "created_at", "sale_date", "timestamp")
        col_gross = pick("gross", "total", "amount", "revenue", "sale_amount")
        col_net = pick("net", "payout", "earnings")
        col_orders = pick("orders", "quantity", "sales", "count")
        col_refunds = pick("refunds", "refunded")

        normalized = []
        for r in rows[:50000]:
            n = {
                "platform": platform,
                "date": (r.get(col_date) if col_date else ""),
                "sku": (r.get(col_sku) if col_sku else sku) or sku,
                "orders": None,
                "gross_cents": None,
                "net_cents": None,
                "refunds": None,
            }
            if col_orders:
                try:
                    n["orders"] = int(float(str(r.get(col_orders) or "0").strip() or 0))
                except Exception:
                    n["orders"] = None
            if col_gross:
                n["gross_cents"] = _to_cents(r.get(col_gross))
            if col_net:
                n["net_cents"] = _to_cents(r.get(col_net))
            if col_refunds:
                try:
                    n["refunds"] = int(float(str(r.get(col_refunds) or "0").strip() or 0))
                except Exception:
                    n["refunds"] = None
            normalized.append(n)

        # write normalized.csv
        norm_path = f"{out_dir}/normalized.csv"
        with open(norm_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["platform","date","sku","orders","gross_cents","net_cents","refunds"])
            w.writeheader()
            for n in normalized:
                w.writerow(n)

        # store in DB (json per row, cheap)
        db.insert_analytics_rows(platform=platform, rows=normalized)

        total_orders = sum([n.get("orders") or 0 for n in normalized])
        total_gross = sum([n.get("gross_cents") or 0 for n in normalized])
        total_net = sum([n.get("net_cents") or 0 for n in normalized])
        total_refunds = sum([n.get("refunds") or 0 for n in normalized])

        summary = {
            "sku_hint": sku,
            "platform": platform,
            "rows": len(normalized),
            "total_orders": total_orders,
            "total_gross_cents": total_gross,
            "total_net_cents": total_net,
            "total_refunds": total_refunds,
            "generated_at": now_iso(),
        }
        rep_path = f"{out_dir}/SUMMARY.json"
        write_json(rep_path, summary)

        md = f"""# Analytics Summary ({platform})

- Rows: {summary['rows']}
- Orders: {summary['total_orders']}
- Gross: ${summary['total_gross_cents']/100:.2f}
- Net: ${summary['total_net_cents']/100:.2f}
- Refunds: {summary['total_refunds']}

Next:
- Run `price_testing_simulator` with this export.
- Run `experiment_runner` if you have variant columns (title/price A/B).
"""
        md_path = f"{out_dir}/REPORT.md"
        write_text(md_path, md)

        return ModuleResult(name=self.name, artifacts=[norm_path, rep_path, md_path], summary=summary)
