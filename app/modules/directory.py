from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import datetime, json, csv

from app.modules.base import ModuleResult
from app.settings import settings
from app.export.packager import write_text
from app.rag.llm import LLM

def _fallback(topic: str) -> str:
    return f"""# Directory Product — {topic}

## What you ship
- directory.csv (schema + starter rows)
- README.md (how to curate + update)
- listing copy + keywords

## 369
- 3 categories
- 6 filters
- 9 featured entries

> Disclaimer: Verify entries and permissions before publishing.
"""


class DirectoryProductModule:
    name = "directory"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        llm = LLM.from_settings()
        niche = constraints.get("niche", topic)
        prompt = f"""Create a directory product blueprint.

Niche: {niche}

Must include:
- A directory schema (CSV columns)
- 3 top-level categories, 6 filters, 9 featured listings
- A refresh plan (Fib cadence: weekly 1, monthly 2, quarterly 3, yearly 5)
- Listing copy: title, subtitle, bullets, keywords
- A 'curation rubric' for accepting entries

Output:
- Provide CSV header + 12 sample rows (fictional placeholders OK)
"""
        text = llm.chat([{"role":"user","content":prompt}])
        if settings.llm_backend.lower().strip() == "none":
            text = _fallback(topic)

        out_dir = Path(settings.data_dir) / "artifacts" / "directory"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        md = out_dir / f"directory__{ts}.md"
        write_text(md, text)

        # write a starter CSV schema (generic)
        csv_path = out_dir / f"directory__{ts}.csv"
        cols = ["name","category","short_desc","url","price","rating","location","tags","notes","last_verified"]
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(cols)
            for i in range(12):
                w.writerow([f"Example {i+1}", "Category A" if i<4 else ("Category B" if i<8 else "Category C"),
                            "Placeholder description", "https://example.com", "", "", "", "tag1;tag2", "", ""])

        meta = {"module": self.name, "topic": topic, "niche": niche, "created_at": datetime.datetime.utcnow().isoformat()}
        j = out_dir / f"directory__{ts}.json"
        j.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return ModuleResult(artifact_paths=[str(md), str(csv_path), str(j)], metadata=meta)
