from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import datetime, json
from app.modules.base import ModuleResult
from app.rag.llm import LLM
from app.settings import settings
from app.export.packager import write_text


import csv
from collections import Counter

class ReviewMinerModule:
    name = "review_miner"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        csv_path = constraints.get("csv_path", "")
        if not csv_path:
            # Produce instructions
            content = """# Review Miner\n\nProvide a local CSV path with columns like: rating, review_text, sku.\nExample constraints:\n{\n  \"csv_path\": \"./data/metrics/reviews.csv\"\n}\n\nThis module will summarize themes and produce copy improvements + FAQ suggestions.\n"""
        else:
            rows = []
            try:
                with open(csv_path, newline="", encoding="utf-8") as f:
                    r = csv.DictReader(f)
                    for row in r:
                        rows.append(row)
            except Exception as e:
                content = f"# Review Miner\n\nFailed to read CSV: {e}\n"
            else:
                texts = [(row.get("review_text") or "").lower() for row in rows]
                # very simple theme mining: top words
                stop = set(["the","and","that","with","this","for","you","your","have","was","are","but","not","they","them","from","just"])
                words=[]
                for t in texts:
                    for w in t.split():
                        w=w.strip(".,:;!?()[]{}<>\"'")
                        if len(w)>=5 and w.isalpha() and w not in stop:
                            words.append(w)
                top = Counter(words).most_common(25)
                lines = ["# Review Miner Summary", "", f"Rows: {len(rows)}", "", "## Top Themes"]
                for w,c in top:
                    lines.append(f"- {w}: {c}")
                lines.append("")
                lines.append("## 369 Copy Improvements")
                lines.append("- 3 headline refinements based on top pain points")
                lines.append("- 6 bullet improvements (clarity + outcomes)")
                lines.append("- 9 FAQ entries (answer recurring objections)")
                content="\n".join(lines)

        out_dir = Path(settings.data_dir) / "artifacts" / "review_miner"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        path = out_dir / f"review_miner__{ts}.md"
        write_text(path, content)
        return ModuleResult([str(path)], {"module": self.name, "topic": topic, "csv_path": csv_path})
