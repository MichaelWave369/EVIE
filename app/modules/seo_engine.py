from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import datetime, json

from app.modules.base import ModuleResult
from app.rag.llm import LLM
from app.settings import settings
from app.export.packager import write_text
from app.flywheel.slug import slugify

FIB_REFRESH_DAYS = [13, 21, 34, 55, 89]

def _default_clusters(topic: str) -> List[dict]:
    # 3 pillars, each with 6 supporting, plus 9 longtails
    base = slugify(topic).replace("-", " ")
    return [
        {"pillar": "How-to", "keywords": [f"how to {base}", f"{base} step by step", f"{base} beginner guide", f"{base} checklist", f"{base} template", f"{base} workflow"]},
        {"pillar": "Comparison", "keywords": [f"best {base} tools", f"{base} vs alternatives", f"{base} pricing", f"{base} software", f"{base} review", f"{base} examples"]},
        {"pillar": "Use-cases", "keywords": [f"{base} for small business", f"{base} for teams", f"{base} for beginners", f"{base} for pros", f"{base} for remote work", f"{base} local-only"]},
    ]

class SEOEngineModule:
    name = "seo_engine"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        niche = constraints.get("niche", "general")
        seed_keywords = constraints.get("seed_keywords") or []
        site_goal = constraints.get("site_goal", "evergreen discovery + conversion")
        key = slugify(topic)
        out_dir = Path(settings.data_dir) / "artifacts" / "seo_engine" / key
        out_dir.mkdir(parents=True, exist_ok=True)

        llm = LLM.from_settings()

        clusters = _default_clusters(topic)
        if seed_keywords:
            clusters.append({"pillar":"Seed Keywords", "keywords": seed_keywords[:12]})

        # LLM brief
        prompt = f"""Create an SEO + evergreen discovery plan aligned to 369/Φ/Fib.

Topic: {topic}
Niche: {niche}
Goal: {site_goal}

Return:
1) 9 article briefs (title + intent + outline + CTA)
2) internal linking plan (hub/spoke)
3) programmatic SEO templates: (X vs Y), (best X for Y), (how to X with Y), (X checklist), (X template)
4) refresh schedule using Fibonacci days: {FIB_REFRESH_DAYS}
Format as Markdown with clear headings.
"""
        plan = llm.chat([{"role":"user","content":prompt}])

        # Write outputs
        created=[]
        write_text(out_dir / "clusters.json", json.dumps(clusters, indent=2))
        created.append(str(out_dir / "clusters.json"))

        write_text(out_dir / "seo_plan.md", plan)
        created.append(str(out_dir / "seo_plan.md"))

        # Programmatic page matrix (CSV)
        matrix_rows=[]
        templates=[
            ("best", "Best {X} for {Y}"),
            ("vs", "{X} vs {Y}"),
            ("howto", "How to {X} with {Y}"),
            ("checklist", "{X} checklist"),
            ("template", "{X} template"),
        ]
        X = topic
        ys = ["beginners","small business","teams","local-only","budget","advanced"]
        for tcode, tname in templates:
            for y in ys:
                matrix_rows.append({"template":tcode, "title":tname.format(X=X, Y=y), "primary_keyword": f"{slugify(X).replace('-',' ')} {y}"})
        csv_path = out_dir / "programmatic_matrix.csv"
        import csv
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w=csv.DictWriter(f, fieldnames=["template","title","primary_keyword"])
            w.writeheader()
            w.writerows(matrix_rows)
        created.append(str(csv_path))

        # Refresh schedule (simple JSON)
        refresh = {"topic": topic, "refresh_days": FIB_REFRESH_DAYS, "note":"Refresh top pages on these Fibonacci day intervals."}
        write_text(out_dir / "refresh_schedule.json", json.dumps(refresh, indent=2))
        created.append(str(out_dir / "refresh_schedule.json"))

        return ModuleResult(created, {"module": self.name, "topic": topic, "niche": niche, "seed_keywords": seed_keywords})
