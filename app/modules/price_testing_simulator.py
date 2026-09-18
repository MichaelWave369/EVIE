from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Tuple
import csv, datetime, json, math, statistics

from app.modules.base import ModuleResult, BaseModule
from app.export.packager import write_text
from app.flywheel.slug import slugify
from app.settings import settings


def _norm(h: str) -> str:
    return (h or "").strip().lower().replace(" ", "_").replace("-", "_")


def _to_float(x: str) -> float:
    try:
        x = (x or "").strip().replace("$","").replace(",","")
        return float(x) if x else 0.0
    except Exception:
        return 0.0


def _phi_ladder(base: float) -> List[float]:
    # Entry / Core / Premium
    return [max(1.0, base * 0.618), max(1.0, base), max(1.0, base * 1.618)]


def _read_csv(path: Path) -> List[Dict[str,str]]:
    rows: List[Dict[str,str]] = []
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append({k: (v or "") for k,v in row.items()})
    return rows


def _detect_cols(headers: List[str]) -> Dict[str,str]:
    hs = [_norm(h) for h in headers]
    def pick(cands):
        for c in cands:
            if c in hs:
                return headers[hs.index(c)]
        return ""
    return {
        "variant": pick(["variant","ab_variant","arm","group","name","test_variant"]),
        "price": pick(["price","price_usd","price_cents","amount","amount_usd"]),
        "views": pick(["views","visitors","impressions","pageviews"]),
        "clicks": pick(["clicks","link_clicks","cta_clicks"]),
        "orders": pick(["orders","sales","purchases","conversions"]),
        "revenue": pick(["revenue","revenue_usd","gross","gross_revenue"]),
        "refunds": pick(["refunds","chargebacks"]),
    }


def _group_key(row: Dict[str,str], cols: Dict[str,str]) -> str:
    v = row.get(cols["variant"], "").strip() if cols["variant"] else ""
    p = row.get(cols["price"], "").strip() if cols["price"] else ""
    if v:
        return v
    if p:
        return p
    return "all"


def _parse_price(raw: str) -> float:
    x = _to_float(raw)
    # treat cents-like values as cents if large
    if x > 500:  # heuristic
        return x / 100.0
    return x


class PriceTestingSimulatorModule(BaseModule):
    name = "price_testing_simulator"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        topic_slug = slugify(topic)
        out_root = self.artifact_root(topic_slug, self.name)

        csv_path = constraints.get("metrics_csv_path") or constraints.get("csv_path") or ""
        base_price = float(constraints.get("base_price", 29.0))
        assumed_elasticity = float(constraints.get("elasticity", -1.1))  # negative
        notes: List[str] = []

        groups = {}
        cols = {}
        if csv_path:
            p = Path(csv_path)
            if not p.is_absolute():
                p = Path(settings.data_dir) / p
            if p.exists():
                rows = _read_csv(p)
                if rows:
                    cols = _detect_cols(list(rows[0].keys()))
                    for r in rows:
                        g = _group_key(r, cols)
                        groups.setdefault(g, []).append(r)
                else:
                    notes.append("CSV had no rows; using synthetic simulation.")
            else:
                notes.append(f"CSV not found at: {p}; using synthetic simulation.")
        else:
            notes.append("No metrics CSV provided; using synthetic simulation.")

        # compute baseline from data if possible
        def summarize(gr_rows: List[Dict[str,str]]) -> Dict[str, float]:
            def s(col):
                if not col: return 0.0
                return sum(_to_float(rr.get(col,"")) for rr in gr_rows)
            views = s(cols.get("views","")) or 0.0
            clicks = s(cols.get("clicks","")) or 0.0
            orders = s(cols.get("orders","")) or 0.0
            revenue = s(cols.get("revenue","")) or 0.0
            refunds = s(cols.get("refunds","")) or 0.0
            # derive price if possible
            price = 0.0
            if cols.get("price"):
                prices = [_parse_price(rr.get(cols["price"], "")) for rr in gr_rows]
                prices = [x for x in prices if x > 0]
                price = statistics.median(prices) if prices else 0.0
            return {"views": views, "clicks": clicks, "orders": orders, "revenue": revenue, "refunds": refunds, "price": price}

        report_lines: List[str] = []
        ts = datetime.datetime.utcnow().isoformat()
        report_lines.append(f"# Price Testing Simulator — {topic}")
        report_lines.append(f"- Generated: {ts}")
        report_lines.append(f"- Alignment: 369 • Φ • Fib")
        report_lines.append("")
        if notes:
            report_lines.append("## Notes")
            report_lines += [f"- {n}" for n in notes]
            report_lines.append("")

        table_rows: List[Tuple[str, float, float, float, float]] = []  # variant, price, conv, rpv, refund_rate

        if groups:
            report_lines.append("## Observed Variant Summary (from CSV)")
            report_lines.append("| Variant | Price | Views | Orders | Conversion | Revenue | Rev/View | Refunds | Refund Rate |")
            report_lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
            for g, rws in groups.items():
                s = summarize(rws)
                price = s["price"] or base_price
                views = s["views"] or 0.0
                orders = s["orders"] or 0.0
                revenue = s["revenue"] or 0.0
                refunds = s["refunds"] or 0.0
                conv = (orders / views) if views else 0.0
                rpv = (revenue / views) if views else 0.0
                rr = (refunds / orders) if orders else 0.0
                report_lines.append(f"| {g} | ${price:.2f} | {views:.0f} | {orders:.0f} | {conv*100:.2f}% | ${revenue:.2f} | ${rpv:.4f} | {refunds:.0f} | {rr*100:.2f}% |")
                table_rows.append((g, price, conv, rpv, rr))
            report_lines.append("")
            # determine winner
            if table_rows:
                winner = max(table_rows, key=lambda t: t[3])  # by rev/view
                report_lines.append(f"**Winner by Revenue/View:** `{winner[0]}` at ${winner[1]:.2f} (Rev/View ${winner[3]:.4f}).")
                report_lines.append("")
                base_price = winner[1]  # use this as baseline for phi ladder
        else:
            report_lines.append("## No observed variants available — running synthetic price simulation")
            report_lines.append("")

        ladder = _phi_ladder(base_price)
        # Use an assumed elasticity model: conv(p) = conv0 * (p/p0)^e
        conv0 = 0.02
        rpv0 = conv0 * base_price
        if table_rows:
            # estimate baseline conv from best available row (use winner row conv)
            winner = max(table_rows, key=lambda t: t[3])
            conv0 = max(0.0001, winner[2])
            rpv0 = conv0 * base_price

        report_lines.append("## Φ Price Ladder Simulation (Entry / Core / Premium)")
        report_lines.append(f"Baseline price: **${base_price:.2f}** | assumed elasticity: **{assumed_elasticity:.2f}**")
        report_lines.append("")
        report_lines.append("| Tier | Price | Expected Conv | Expected Rev/View |")
        report_lines.append("|---|---:|---:|---:|")
        tier_names = ["Entry (0.618Φ)", "Core (1.0)", "Premium (1.618Φ)"]
        sims = []
        for tier, price in zip(tier_names, ladder):
            # normalized conv
            conv = conv0 * ((price / base_price) ** assumed_elasticity)
            rpv = conv * price
            sims.append((tier, price, conv, rpv))
            report_lines.append(f"| {tier} | ${price:.2f} | {conv*100:.2f}% | ${rpv:.4f} |")
        report_lines.append("")
        best = max(sims, key=lambda t: t[3])
        report_lines.append(f"**Simulated best revenue/view:** {best[0]} at ${best[1]:.2f} (≈ ${best[3]:.4f} per view).")
        report_lines.append("")

        # 3/6/9 action plan + Fib cadence
        report_lines.append("## 3 / 6 / 9 Test Plan (Fib cadence)")
        report_lines.append("### 3 Variants")
        report_lines.append(f"- A: ${ladder[0]:.2f} (Entry)")
        report_lines.append(f"- B: ${ladder[1]:.2f} (Core)")
        report_lines.append(f"- C: ${ladder[2]:.2f} (Premium)")
        report_lines.append("")
        report_lines.append("### 6-Day Run")
        report_lines.append("- Days 1–2: baseline traffic capture, ensure tracking columns exist")
        report_lines.append("- Days 3–5: steady state (no copy changes)")
        report_lines.append("- Day 6: export CSV, run simulator, lock winner")
        report_lines.append("")
        report_lines.append("### 9-Day Optimize")
        report_lines.append("- Rotate headline/thumbnail A/B under the winning price")
        report_lines.append("- Add order bump (0.382Φ of core price) for lift")
        report_lines.append("")

        out_md = "\n".join(report_lines)
        report_path = out_root / "PRICE_REPORT.md"
        write_text(report_path, out_md)

        meta = {
            "topic_slug": topic_slug,
            "base_price": base_price,
            "ladder": ladder,
            "used_csv": bool(csv_path and groups),
        }
        return ModuleResult(artifact_paths=[str(report_path)], metadata=meta)
