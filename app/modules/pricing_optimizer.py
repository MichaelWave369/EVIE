from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import datetime, json
from app.modules.base import ModuleResult
from app.rag.llm import LLM
from app.settings import settings
from app.export.packager import write_text


import sqlite3
from app.db.schema import connect

class PricingOptimizerModule:
    name = "pricing_optimizer"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        con = connect()
        products = con.execute("SELECT sku,name,price_cents,status FROM products ORDER BY created_at DESC LIMIT 200").fetchall()
        con.close()

        # simple heuristic: suggest 3-tier ladder around median
        prices = [p["price_cents"] for p in products if p["price_cents"] is not None and p["price_cents"] > 0]
        median = sorted(prices)[len(prices)//2] if prices else 2900
        entry = int(max(900, median * 0.618))
        core = int(median)
        premium = int(median * 1.618)

        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        out_dir = Path(settings.data_dir) / "artifacts" / "pricing_optimizer"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"pricing_plan__{ts}.md"

        lines = []
        lines.append(f"# Pricing Plan (Local-Only)\nGenerated: {datetime.datetime.utcnow().isoformat()}Z\n")
        lines.append("## Φ Ladder Suggestion\n")
        lines.append(f"- Entry: ${entry/100:.2f}\n- Core: ${core/100:.2f}\n- Premium: ${premium/100:.2f}\n")
        lines.append("\n## 369 A/B Tests\n")
        lines.append("- 3 title variants\n- 6 thumbnail/cover variants\n- 9 bullet/CTA variants\n")
        lines.append("\n## Recent Products (last 200)\n")
        for p in products[:30]:
            lines.append(f"- {p['sku']} — {p['name']} — ${p['price_cents']/100:.2f} — {p['status']}")
        write_text(path, "\n".join(lines))

        return ModuleResult([str(path)], {"module": self.name, "entry_cents": entry, "core_cents": core, "premium_cents": premium})
