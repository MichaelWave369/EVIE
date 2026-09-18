from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List
import datetime
import os

from app.modules.base import ModuleResult
from app.rag.llm import LLM
from app.settings import settings
from app.export.packager import write_text


class OfferQAGateModule:
    """Offer QA Gate

    Creates a structured QA report for an offer bundle.

    If constraints contains `artifact_paths` (list[str]), it will inspect those files.
    Otherwise it will do a best-effort scan of the artifacts folder for the newest files.
    """

    name = "offer_qa_gate"

    def _collect_paths(self, constraints: Dict[str, Any]) -> List[str]:
        paths = constraints.get("artifact_paths") or []
        if isinstance(paths, list) and paths:
            return [str(p) for p in paths]

        # Best-effort fallback: newest artifacts
        root = Path(settings.data_dir) / "artifacts"
        if not root.exists():
            return []
        files = [p for p in root.rglob("*") if p.is_file()]
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return [str(p) for p in files[:25]]

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        llm = LLM.from_settings()
        paths = self._collect_paths(constraints)

        manifest = []
        for p in paths:
            fp = Path(p)
            if not fp.exists():
                continue
            manifest.append(
                {
                    "path": str(fp),
                    "name": fp.name,
                    "ext": fp.suffix.lower(),
                    "bytes": int(fp.stat().st_size),
                }
            )

        # Heuristic checks
        exts = {m["ext"] for m in manifest}
        has_zip = ".zip" in exts
        has_pdf = ".pdf" in exts
        has_md = ".md" in exts
        has_png = ".png" in exts
        has_jpg = ".jpg" in exts or ".jpeg" in exts
        has_csv = ".csv" in exts

        required = {
            "core_content": has_md or has_pdf,
            "listing_images": has_png or has_jpg,
            "download_bundle": has_zip,
            "data_tables_optional": has_csv,
        }
        missing = [k for k, ok in required.items() if not ok and k != "data_tables_optional"]

        # Simple score: start at 100, subtract for missing
        score = 100
        score -= 25 * len(missing)
        score = max(0, min(100, score))

        prompt = f"""You are the Offer QA Gate for a local-only passive income engine.

Topic: {topic}

Artifacts manifest (name | ext | bytes):
""" + "\n".join([f"- {m['name']} | {m['ext']} | {m['bytes']}" for m in manifest]) + """

Heuristic status:
- core_content: {required['core_content']}
- listing_images: {required['listing_images']}
- download_bundle: {required['download_bundle']}
- data_tables_optional: {required['data_tables_optional']}

Compute a QA report that is:
- 369 aligned: 3 critical blockers, 6 major improvements, 9 nice-to-haves
- Φ aligned: ~61.8% clarity/value improvements, ~38.2% risk/friction reductions
- Fibonacci cadence: next actions in 1/2/3/5/8 day plan

Return:
1) A short PASS/CONDITIONAL/FAIL verdict
2) A numeric score 0-100 (you may reuse {score})
3) A checklist section the user can follow
4) Copy-ready "Store Listing QA" (headline, bullets, FAQ prompts)
5) A minimal compliance reminder (no guarantees; add disclosures where relevant)
"""

        report_md = llm.chat([{"role": "user", "content": prompt}])

        out_dir = Path(settings.data_dir) / "artifacts" / "qa"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        md_path = out_dir / f"qa__{ts}.md"
        json_path = out_dir / f"qa__{ts}.json"

        write_text(md_path, report_md)
        write_text(
            json_path,
            __import__("json").dumps(
                {
                    "topic": topic,
                    "score": score,
                    "missing": missing,
                    "required": required,
                    "manifest": manifest,
                },
                indent=2,
            ),
        )

        return ModuleResult(
            artifact_paths=[str(md_path), str(json_path)],
            metadata={"topic": topic, "module": self.name, "score": score, "missing": missing},
        )
