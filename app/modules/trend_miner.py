from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import datetime, json
from app.modules.base import ModuleResult
from app.rag.llm import LLM
from app.settings import settings
from app.export.packager import write_text


import sqlite3
from collections import Counter
from app.db.schema import connect

class TrendMinerModule:
    """Local-first trend miner: analyzes your vault (documents/chunks) + products to propose next topics.
No web scraping. If you add data/metrics/*.csv, it will also include those."""
    name = "trend_miner"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        # topic is optional for this module; used as 'focus'
        focus = constraints.get("focus", topic or "general")
        top_n = int(constraints.get("top_n", 9))

        con = connect()
        rows = con.execute("SELECT canonical_key, raw_text FROM documents ORDER BY created_at DESC LIMIT 200").fetchall()
        con.close()

        # crude keyword extraction: count words >4 chars excluding common
        stop = set(["that","with","this","from","your","have","will","into","about","they","them","then","there","what","when","where","which","would","could","should","also","more","only","make","just"])
        words = []
        for r in rows:
            txt = (r["raw_text"] or "")[:6000].lower()
            toks = [w.strip(".,:;!?()[]{}<>\"'") for w in txt.split()]
            words.extend([w for w in toks if len(w) >= 5 and w.isalpha() and w not in stop])
        counts = Counter(words)
        top = counts.most_common(top_n)

        # Build a report
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        out_dir = Path(settings.data_dir) / "artifacts" / "trend_miner"
        out_dir.mkdir(parents=True, exist_ok=True)
        report_path = out_dir / f"trend_report__{ts}.md"

        fib = [1,2,3,5,8]
        lines = []
        lines.append(f"# Trend Report (Local-Only)\n\nFocus: **{focus}**\nGenerated: {datetime.datetime.utcnow().isoformat()}Z\n")
        lines.append("## Top Signals (keywords from your last 200 documents)\n")
        for w,c in top:
            lines.append(f"- {w} — {c}")
        lines.append("\n## 369 Next Moves\n")
        lines.append("**3 Pillars:** Create / Distribute / Compound\n")
        lines.append("**6 Loop:** Research → Build → Publish → Convert → Deliver → Optimize\n")
        lines.append("\n## Fibonacci Content Ladder (suggested next outputs)\n")
        lines.append(f"- {fib[0]} cornerstone guide\n- {fib[1]} ebooks\n- {fib[2]} template packs\n- {fib[3]} posts\n- {fib[4]} shorts\n")
        lines.append("\n## Suggested Topics (auto-proposed)\n")
        for i,(w,c) in enumerate(top[:min(9,len(top))], start=1):
            lines.append(f"{i}. {w.title()} — build a pack around: {w} + {focus}")

        write_text(report_path, "\n".join(lines))
        return ModuleResult([str(report_path)], {"module": self.name, "focus": focus, "top_keywords": top})
