
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List, Tuple
import csv, json, datetime, math

from app.modules.base import ModuleResult
from app.settings import settings
from app.export.packager import write_text
from app.flywheel.slug import slugify

def _num(x):
    try:
        if x is None: return 0.0
        s = str(x).strip().replace(",","")
        return float(s) if s else 0.0
    except Exception:
        return 0.0

def _pick_col(cols: List[str], candidates: List[str]) -> str | None:
    cols_l = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand.lower() in cols_l:
            return cols_l[cand.lower()]
    return None

def _z_test(p1, n1, p2, n2):
    # Two-proportion z test (approx). Returns z, p-value approx using normal cdf.
    if n1 <= 0 or n2 <= 0:
        return 0.0, 1.0
    p_pool = (p1*n1 + p2*n2) / (n1+n2)
    denom = math.sqrt(max(p_pool*(1-p_pool)*(1/n1 + 1/n2), 1e-12))
    z = (p1 - p2) / denom
    # normal CDF approx
    p = 2*(1 - 0.5*(1+math.erf(abs(z)/math.sqrt(2))))
    return z, p

class ExperimentRunnerModule:
    name = "experiment_runner"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        key = slugify(topic)
        out_dir = Path(settings.data_dir) / "artifacts" / "experiment_runner" / key
        out_dir.mkdir(parents=True, exist_ok=True)

        csv_path = constraints.get("metrics_csv_path") or constraints.get("csv_path")
        if not csv_path:
            # allow passing through a metrics run path
            csv_path = constraints.get("path")
        if not csv_path:
            report = "# Experiment Runner\n\nNo CSV provided. Provide `metrics_csv_path` pointing to a local export.\n"
            write_text(out_dir / "REPORT.md", report)
            return ModuleResult([str(out_dir/"REPORT.md")], {"module": self.name, "status":"no_csv"})

        p = Path(csv_path)
        if not p.exists():
            report = f"# Experiment Runner\n\nCSV not found: `{csv_path}`\n"
            write_text(out_dir / "REPORT.md", report)
            return ModuleResult([str(out_dir/"REPORT.md")], {"module": self.name, "status":"missing_csv", "path": csv_path})

        rows=[]
        with p.open("r", encoding="utf-8", errors="ignore", newline="") as f:
            reader = csv.DictReader(f)
            cols = reader.fieldnames or []
            var_col = constraints.get("variant_col") or _pick_col(cols, ["variant","test","arm","headline","creative","offer"])
            imp_col = constraints.get("impressions_col") or _pick_col(cols, ["impressions","views","visits","sessions"])
            clk_col = constraints.get("clicks_col") or _pick_col(cols, ["clicks","click"])
            conv_col = constraints.get("conversions_col") or _pick_col(cols, ["purchases","orders","conversions","sales","subs"])
            rev_col = constraints.get("revenue_col") or _pick_col(cols, ["revenue","gross","amount","usd"])

            for r in reader:
                rows.append(r)

        if not rows:
            write_text(out_dir / "REPORT.md", "# Experiment Runner\n\nCSV had no rows.\n")
            return ModuleResult([str(out_dir/"REPORT.md")], {"module": self.name, "status":"empty"})

        # aggregate by variant
        agg={}
        for r in rows:
            v = (r.get(var_col) if var_col else None) or "A"
            a = agg.setdefault(v, {"impressions":0.0,"clicks":0.0,"conversions":0.0,"revenue":0.0,"rows":0})
            a["impressions"] += _num(r.get(imp_col)) if imp_col else 0.0
            a["clicks"] += _num(r.get(clk_col)) if clk_col else 0.0
            a["conversions"] += _num(r.get(conv_col)) if conv_col else 0.0
            a["revenue"] += _num(r.get(rev_col)) if rev_col else 0.0
            a["rows"] += 1

        # compute rates
        table=[]
        for v, a in agg.items():
            imp=a["impressions"] or 0.0
            clk=a["clicks"] or 0.0
            conv=a["conversions"] or 0.0
            ctr = (clk/imp) if imp>0 else 0.0
            cvr = (conv/max(clk,1.0)) if clk>0 else (conv/max(imp,1.0))
            rpc = (a["revenue"]/max(conv,1.0)) if conv>0 else 0.0
            table.append((v, imp, clk, conv, a["revenue"], ctr, cvr, rpc))
        table.sort(key=lambda x: (x[6], x[5], x[4]), reverse=True)  # cvr, ctr, revenue

        winner = table[0][0]
        # compare winner vs runner-up (if present)
        significance = {}
        if len(table) >= 2:
            w = next(a for v,a in agg.items() if v==winner)
            r2 = table[1][0]
            b = next(a for v,a in agg.items() if v==r2)
            # Use conversion rate per click if clicks exist, else per impression
            n1 = w["clicks"] if w["clicks"]>0 else w["impressions"]
            n2 = b["clicks"] if b["clicks"]>0 else b["impressions"]
            p1 = (w["conversions"]/max(n1,1.0))
            p2 = (b["conversions"]/max(n2,1.0))
            z,pv = _z_test(p1, max(n1,1.0), p2, max(n2,1.0))
            significance = {"compare_to": r2, "z": z, "p_value": pv, "p1": p1, "p2": p2, "n1": n1, "n2": n2}

        # Write report
        lines=[]
        lines.append(f"# Experiment Runner — {topic}\n")
        lines.append(f"- Source CSV: `{p}`\n- Variant column: `{var_col}`\n")
        lines.append(f"## Winner\n- **{winner}** (highest conversion rate)\n")
        if significance:
            lines.append(f"- vs **{significance['compare_to']}**: z={significance['z']:.3f}, p≈{significance['p_value']:.3f}\n")
        lines.append("\n## Table\n")
        lines.append("| Variant | Impressions | Clicks | Conversions | Revenue | CTR | CVR | Rev/Conv |\n|---|---:|---:|---:|---:|---:|---:|---:|\n")
        for v, imp, clk, conv, rev, ctr, cvr, rpc in table:
            lines.append(f"| {v} | {int(imp)} | {int(clk)} | {int(conv)} | {rev:.2f} | {ctr*100:.2f}% | {cvr*100:.2f}% | {rpc:.2f} |\n")

        lines.append("\n## Next 369 Test Plan\n")
        lines.append("**3** new headlines based on the winner\n**6** thumbnail directions to test\n**9** hooks/angles to rotate for shorts & listings\n")
        lines.append("\n## Fibonacci cadence\n- Day 1: deploy winner\n- Day 2: launch 3 headline variants\n- Day 3: add 6 bullets refinement\n- Day 5: rerun metrics + pick winner\n- Day 8: fold winner into product registry + update listing pack\n")

        report = "".join(lines)
        write_text(out_dir / "REPORT.md", report)

        meta = {
            "module": self.name,
            "winner": winner,
            "variants": [v for v,_imp,_clk,_conv,_rev,_ctr,_cvr,_rpc in table],
            "significance": significance,
            "generated_at": datetime.datetime.utcnow().isoformat(),
        }
        write_text(out_dir / "SUMMARY.json", json.dumps(meta, indent=2))
        return ModuleResult([str(out_dir/"REPORT.md"), str(out_dir/"SUMMARY.json")], meta)
