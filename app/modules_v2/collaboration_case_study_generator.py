from __future__ import annotations
from typing import Any
import os, json
from .base import ModuleResult
from .utils import ensure_dir, write_text, write_json, now_iso

class CollaborationCaseStudyGenerator:
    """Documents how a product was built (meta-product)."""
    name = "collaboration_case_study_generator"

    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        out_dir = f"{run_folder}/artifacts/{self.name}"
        ensure_dir(out_dir)

        artifact_map_path = os.path.join(run_folder, "ARTIFACT_MAP.json")
        modules_used = []
        if os.path.exists(artifact_map_path):
            try:
                with open(artifact_map_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                modules_used = [r.get("module") for r in (data or []) if r.get("module")]
            except Exception:
                modules_used = []

        md = f"""# Collaboration Case Study — {topic}

This is a **process documentation pack**: how this SKU was produced using a local-first toolchain.

## 3 Roles
1) Human: goals, constraints, judgment
2) AI: drafting, structuring, iteration
3) System: packaging, stamping, versioning

## 6 Steps
1) Define the outcome + boundaries
2) Generate artifacts (module chain)
3) QA gate + edits
4) Bundle + stamp (proof-of-creation)
5) Platform pack exports
6) Iterate using metrics + experiments

## 9 Receipts (fill in / attach)
1) Goal statement
2) Input notes
3) Module chain
4) Draft artifacts
5) Edits made by human
6) Final bundle hash
7) Listing copy
8) Testimonials
9) Metrics snapshot

## Modules used
- """ + "\n- ".join(modules_used or ["(artifact map missing)"]) + """


## Prompt log (template)
- System prompt:
- User prompt:
- Constraints:
- What changed after iteration?

## Notes
- No guarantees.
- Keep personal data out of packs you sell.
"""
        md_path = f"{out_dir}/CASE_STUDY.md"
        write_text(md_path, md)
        write_json(f"{out_dir}/case_study.json", {"sku": sku, "topic": topic, "generated_at": now_iso(), "modules_used": modules_used})
        return ModuleResult(name=self.name, artifacts=[md_path, f"{out_dir}/case_study.json"], summary={"modules_used": len(modules_used)})
