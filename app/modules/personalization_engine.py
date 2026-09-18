from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import datetime, json, csv

from app.modules.base import ModuleResult
from app.rag.llm import LLM
from app.settings import settings
from app.export.packager import write_text
from app.flywheel.slug import slugify

DEFAULT_EDITIONS = [
    {"edition":"Home", "tag":"home", "who":"individuals", "angle":"simple, personal, low-cost"},
    {"edition":"Biz", "tag":"biz", "who":"small business", "angle":"team workflows, ROI, compliance"},
    {"edition":"Hotel", "tag":"hotel", "who":"hospitality", "angle":"guests, ops, reliability"},
    {"edition":"School", "tag":"school", "who":"K-12", "angle":"safety, policies, admin"},
    {"edition":"University", "tag":"university", "who":"higher ed", "angle":"departments, research, scale"},
]

DEFAULT_PERSONAS = [
    {"persona":"Beginner", "tag":"beginner", "tone":"simple, friendly"},
    {"persona":"Operator", "tag":"operator", "tone":"procedural, checklist"},
    {"persona":"Executive", "tag":"exec", "tone":"strategic, KPI-driven"},
]

class PersonalizationEngineModule:
    name = "personalization_engine"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        editions = constraints.get("editions") or DEFAULT_EDITIONS
        personas = constraints.get("personas") or DEFAULT_PERSONAS
        niche = constraints.get("niche", "general")

        llm = LLM.from_settings()
        key = slugify(topic)
        out_dir = Path(settings.data_dir) / "artifacts" / "personalization_engine" / key
        out_dir.mkdir(parents=True, exist_ok=True)

        created=[]

        # Plan
        plan_prompt = f"""Create a mass-personalization plan for a product line.

Topic: {topic}
Niche: {niche}

We will generate editions and personas. Use 369/Φ/Fib alignment:
- 3 core promises that remain consistent across variants
- 6 adjustable knobs (tone, complexity, compliance, pricing, examples, support)
- 9 variant outputs (editions/personas mix)

Return:
1) Canonical promise + positioning
2) Variant matrix (editions × personas) with short pitch + key features
3) Suggested SKU naming scheme
4) Module constraints suggestions for each variant (so the generator can reuse the same base modules)
"""
        plan_md = llm.chat([{"role":"user","content":plan_prompt}])
        write_text(out_dir / "personalization_plan.md", plan_md)
        created.append(str(out_dir / "personalization_plan.md"))

        # SKU map
        rows=[]
        for e in editions:
            for p in personas:
                sku = f"EV369-{key}-{e.get('tag')}-{p.get('tag')}"
                variant_topic = f"{topic} — {e.get('edition')} Edition ({p.get('persona')})"
                rows.append({
                    "sku": sku,
                    "variant_topic": variant_topic,
                    "edition": e.get("edition"),
                    "persona": p.get("persona"),
                    "who": e.get("who"),
                    "angle": e.get("angle"),
                    "tone": p.get("tone"),
                })
        csv_path = out_dir / "sku_map.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w=csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        created.append(str(csv_path))

        # Constraints template JSON for reuse
        constraints_out=[]
        for r in rows[:9]:  # keep 9 default variants
            constraints_out.append({
                "sku": r["sku"],
                "topic": r["variant_topic"],
                "constraints_by_module": {
                    "offer_ladder": {"niche": niche},
                    "conversion_packager": {"tone": r["tone"]},
                    "funnel_engine": {"niche": niche},
                    "platform_packs": {"platforms": ["gumroad","etsy","kdp"]},
                    "seo_engine": {"niche": niche, "seed_keywords": [r["edition"], r["persona"]]},
                }
            })
        json_path = out_dir / "variant_constraints.json"
        write_text(json_path, json.dumps(constraints_out, indent=2))
        created.append(str(json_path))

        return ModuleResult(created, {"module": self.name, "topic": topic, "niche": niche, "variants": len(rows)})
