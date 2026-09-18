from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List, Tuple
import csv, datetime, json
from app.modules.base import ModuleResult, BaseModule
from app.export.packager import write_text
from app.flywheel.slug import slugify

NUM_KEYS = {"views","impressions","clicks","sales","orders","revenue","revenue_usd","refunds","subs","subscribers","optins","ctr","conversion"}

def _to_float(x: str) -> float:
    try:
        x = (x or "").strip().replace("$","").replace(",","")
        if x == "":
            return 0.0
        return float(x)
    except Exception:
        return 0.0

def _normalize_header(h: str) -> str:
    h = (h or "").strip().lower()
    h = h.replace(" ", "_").replace("-","_")
    return h

def summarize_rows(rows: List[Dict[str,str]]) -> Dict[str, Any]:
    totals = {}
    for r in rows:
        for k,v in r.items():
            nk = _normalize_header(k)
            if nk in NUM_KEYS:
                totals[nk] = totals.get(nk, 0.0) + _to_float(v)
    views = totals.get("views", totals.get("impressions", 0.0))
    clicks = totals.get("clicks", 0.0)
    sales = totals.get("sales", totals.get("orders", 0.0))
    revenue = totals.get("revenue", totals.get("revenue_usd", 0.0))
    refunds = totals.get("refunds", 0.0)
    subs = totals.get("subs", totals.get("subscribers", totals.get("optins", 0.0)))

    ctr = (clicks / views) if views > 0 else 0.0
    conv = (sales / clicks) if clicks > 0 else 0.0
    aov = (revenue / sales) if sales > 0 else 0.0
    refund_rate = (refunds / sales) if sales > 0 else 0.0

    return {
        "totals": totals,
        "derived": {
            "views": views,
            "clicks": clicks,
            "sales": sales,
            "revenue": revenue,
            "ctr": ctr,
            "conversion_rate": conv,
            "aov": aov,
            "refund_rate": refund_rate,
            "subs": subs,
        }
    }

def recommendations(summary: Dict[str, Any]) -> List[str]:
    d = summary["derived"]
    recs = []
    # 369 framing: 3 levers for each stage
    if d["views"] > 0 and d["ctr"] < 0.01:
        recs.append("CTR is low → Improve thumbnails/titles (3 variants) + test 6 days + keep 1 winner (369 loop).")
    if d["clicks"] > 30 and d["conversion_rate"] < 0.02:
        recs.append("Conversion is low → Strengthen landing page: clearer promise, proof, FAQ, and guarantee boundaries.")
    if d["sales"] > 0 and d["refund_rate"] > 0.08:
        recs.append("Refunds are high → Add onboarding, quick-start guide, and support macros; reduce expectation mismatch.")
    if d["aov"] < 25 and d["sales"] > 5:
        recs.append("AOV is low → Introduce Φ offer ladder: $9 entry, $49 core, $199 premium/licensing.")
    if d["subs"] > 0 and d["sales"] == 0:
        recs.append("List is growing but sales are zero → Add Fib 5-email sequence + one-time offer bundle.")
    if not recs:
        recs.append("Metrics look stable → Next: repurpose top topic into 1/2/3/5/8 outputs and release v+1.")
    return recs

class MetricsOptimizerModule(BaseModule):
    name = "metrics_optimizer"
    display_name = "Metrics Import + Optimizer"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        # Accept CSV text, or a file path in constraints
        csv_text = constraints.get("csv_text")
        csv_path = constraints.get("csv_path")
        rows: List[Dict[str,str]] = []
        if csv_path:
            p = Path(csv_path)
            if p.exists():
                csv_text = p.read_text(encoding="utf-8", errors="ignore")

        if not csv_text:
            # Create an empty template schema
            out = Path("data/artifacts/metrics") / slugify(topic)
            out.mkdir(parents=True, exist_ok=True)
            template = "date,views,clicks,sales,revenue,refunds,subs\n"
            write_text(out/"metrics_template.csv", template)
            write_text(out/"README.md", "Drop your exported metrics CSV here, then rerun Metrics Optimizer.\n")
            return ModuleResult(
                artifact_paths=[str(out/"metrics_template.csv"), str(out/"README.md")],
                metadata={"status":"template_created"}
            )

        reader = csv.DictReader(csv_text.splitlines())
        for r in reader:
            rows.append(r)

        summary = summarize_rows(rows)
        recs = recommendations(summary)
        report_md = f"""# Metrics Optimizer Report — {topic}

## Totals
```json
{json.dumps(summary['totals'], indent=2)}
```

## Derived KPIs
```json
{json.dumps(summary['derived'], indent=2)}
```

## 369 / Φ / Fib Recommendations
""" + "\n".join([f"- {r}" for r in recs]) + "\n"

        out = Path("data/artifacts/metrics") / slugify(topic)
        out.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        md_path = out / f"metrics_report_{ts}.md"
        json_path = out / f"metrics_summary_{ts}.json"
        write_text(md_path, report_md)
        write_text(json_path, json.dumps({"summary": summary, "recommendations": recs}, indent=2))

        return ModuleResult(
            artifact_paths=[str(md_path), str(json_path)],
            metadata={"rows": len(rows), "kpis": summary["derived"], "recommendations": recs}
        )
