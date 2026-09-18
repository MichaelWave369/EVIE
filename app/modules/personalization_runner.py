
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import datetime, json

from app.modules.base import ModuleResult
from app.settings import settings
from app.export.packager import write_text
from app.flywheel.slug import slugify
from app.db import queries

def _find_variant_constraints(artifact_paths: List[str]) -> Path | None:
    for p in artifact_paths or []:
        try:
            pp = Path(p)
            if pp.exists() and pp.name.lower() in {"variant_constraints.json","variant_constraints.json".lower()}:
                return pp
            if pp.exists() and pp.name.lower().endswith("variant_constraints.json"):
                return pp
        except Exception:
            continue
    return None

class PersonalizationRunnerModule:
    name = "personalization_runner"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        key = slugify(topic)
        out_dir = Path(settings.data_dir) / "artifacts" / "personalization_runner" / key
        out_dir.mkdir(parents=True, exist_ok=True)

        artifact_paths = constraints.get("artifact_paths") or []
        vc_path = constraints.get("variant_constraints_path")
        if vc_path:
            vc = Path(vc_path)
        else:
            vc = _find_variant_constraints(artifact_paths)

        if not vc or not vc.exists():
            msg = (
                "# Personalization Runner\n\n"
                "No `variant_constraints.json` found.\n\n"
                "Run `personalization_engine` first, then pass its constraints file path via:\n"
                "`constraints: {\"variant_constraints_path\": \".../variant_constraints.json\"}`\n"
            )
            write_text(out_dir / "REPORT.md", msg)
            return ModuleResult([str(out_dir/"REPORT.md")], {"module": self.name, "status":"missing_constraints"})

        data = json.loads(vc.read_text(encoding="utf-8", errors="ignore") or "{}")
        variants = data.get("variants") or []
        if not isinstance(variants, list) or not variants:
            write_text(out_dir / "REPORT.md", "# Personalization Runner\n\nNo variants found in constraints.\n")
            return ModuleResult([str(out_dir/"REPORT.md")], {"module": self.name, "status":"no_variants"})

        # Choose modules for each variant build
        default_modules = constraints.get("modules") or data.get("recommended_modules") or [
            "offer_ladder","conversion_packager","platform_packs","seo_engine","funnel_engine",
            "brandkit_cover_factory","creative_factory","terms_generator","ab_kit_generator","offer_qa_gate"
        ]
        if isinstance(default_modules, str):
            default_modules = [m.strip() for m in default_modules.split(",") if m.strip()]

        created=[]
        priority = int(constraints.get("priority", 1))

        for i, v in enumerate(variants[:21], start=1):  # keep bounded
            vname = v.get("name") or v.get("sku_suffix") or f"variant_{i:02d}"
            vtopic = f"{topic} — {vname}".strip()
            vconstraints = {"variant": v, "base_topic": topic, "alignment": "369 • Φ • Fib"}
            # allow per-module constraints pass-through
            per_mod = constraints.get("constraints_by_module") or {}
            merged = {"__variant": vconstraints, **per_mod}
            qid = queries.enqueue_queue_item(vtopic, default_modules, merged, priority=priority)
            created.append({"queue_id": qid, "topic": vtopic, "modules": default_modules, "variant": v})

        report_lines = []
        report_lines.append(f"# Personalization Runner — {topic}\n\n")
        report_lines.append(f"Found constraints: `{vc}`\n\n")
        report_lines.append(f"Enqueued **{len(created)}** variant builds into Product Factory queue.\n\n")
        report_lines.append("## Variants enqueued (3/6/9 preview)\n")
        for row in created[:9]:
            report_lines.append(f"- Queue #{row['queue_id']}: **{row['topic']}**\n")
        if len(created) > 9:
            report_lines.append(f"\n(+{len(created)-9} more)\n")

        report_lines.append("\n## Next Steps\n")
        report_lines.append("1) Run `Factory → Run Next` (dashboard) or `POST /v1/factory/run_next`\n")
        report_lines.append("2) Let the worker loop build through the queue (Fib cadence)\n")
        report_lines.append("3) Export catalog when ready: `POST /v1/factory/export_catalog`\n")

        report = "".join(report_lines)
        write_text(out_dir / "REPORT.md", report)
        write_text(out_dir / "variant_queue.json", json.dumps(created, indent=2))

        meta = {
            "module": self.name,
            "queued": len(created),
            "queue_ids": [c["queue_id"] for c in created],
            "constraints_path": str(vc),
            "generated_at": datetime.datetime.utcnow().isoformat(),
        }
        write_text(out_dir / "SUMMARY.json", json.dumps(meta, indent=2))
        return ModuleResult([str(out_dir/"REPORT.md"), str(out_dir/"variant_queue.json"), str(out_dir/"SUMMARY.json")], meta)
