
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List
import datetime, json, sqlite3

from app.modules.base import ModuleResult
from app.settings import settings
from app.flywheel.slug import slugify
from app.export.packager import write_text, package_bundle

def _connect_db() -> sqlite3.Connection:
    return sqlite3.connect(settings.db_path)

def _safe_json(s: str):
    try:
        return json.loads(s)
    except Exception:
        return {}

class DatasetToProductPipelineModule:
    name = "dataset_to_product_pipeline"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        slug = slugify(topic)
        out_dir = settings.data_dir / "artifacts" / "dataset_to_product" / slug
        out_dir.mkdir(parents=True, exist_ok=True)

        max_docs = int(constraints.get("max_docs", 21))
        include_full_text = bool(constraints.get("include_full_text", False))
        max_safety_tier = int(constraints.get("max_safety_tier", 1))

        if not settings.db_path.exists():
            write_text(out_dir / "README.md", "No local DB found yet. Run ingestion first (v1/ingest/*), then rerun this module.")
            return ModuleResult(artifact_paths=[str(out_dir / "README.md")], metadata={"status":"no_db"})

        conn = _connect_db()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Only include docs that are shareable or low safety tier
        # shareable is optional metadata_json flag; if absent, fall back to safety tier check.
        q = """
        SELECT d.doc_id, d.source_id, d.metadata_json, d.raw_text, d.created_at,
               d.domain_id, d.phase_id, d.state_id, d.lens_id, d.canonical_key,
               s.title as source_title, s.source_type, s.source_uri
        FROM documents d
        LEFT JOIN sources s ON s.source_id = d.source_id
        ORDER BY d.created_at DESC
        LIMIT ?
        """
        rows = cur.execute(q, (max_docs*3,)).fetchall()

        picked = []
        for r in rows:
            meta = _safe_json(r["metadata_json"])
            shareable = bool(meta.get("shareable", False))
            safety = int(meta.get("safety_tier", 0))
            # if lens safety present in metadata, trust it; else allow low tier by default
            if shareable or safety <= max_safety_tier:
                picked.append((r, meta))
            if len(picked) >= max_docs:
                break

        docs_export = []
        for r, meta in picked:
            text = r["raw_text"] or ""
            docs_export.append({
                "doc_id": r["doc_id"],
                "title": (r["source_title"] or meta.get("title") or f"Doc {r['doc_id']}"),
                "created_at": r["created_at"],
                "canonical_key": r["canonical_key"],
                "tags": meta.get("tags", []),
                "excerpt": text[:800],
                "domain_id": r["domain_id"],
                "phase_id": r["phase_id"],
                "state_id": r["state_id"],
                "lens_id": r["lens_id"],
                "source_type": r["source_type"],
            })
            if include_full_text:
                docs_export[-1]["raw_text"] = text

        # Build human-friendly index
        lines = [f"# Reference Pack — {topic}", "", "## What this is", 
                 "A curated export of your **local EmberVault documents** packaged as a sellable reference pack.",
                 "Only includes docs that are marked `shareable=true` in metadata OR are under the allowed safety tier.",
                 "",
                 "## Contents (top 21 max)",
                 ""]
        for d in docs_export:
            ck = d.get("canonical_key") or ""
            lines.append(f"- **{d['title']}**  ({d['created_at']})  {('['+ck+']') if ck else ''}")
        lines.append("")
        lines.append("## Suggested queries (3/6/9)")
        lines.append("- 3: What are the core pillars in this pack?")
        lines.append("- 6: Give me a step-by-step workflow based on these documents.")
        lines.append("- 9: List the top objections and how the docs address them.")
        lines.append("")
        lines.append("## Notes")
        lines.append("- Review content before selling.")
        lines.append("- Never include private customer data; keep exports opt-in and anonymized.")
        index_md = "\n".join(lines)

        write_text(out_dir / "INDEX.md", index_md)
        write_text(out_dir / "documents.json", json.dumps(docs_export, indent=2))

        readme = f"""# Reference Pack Build — {topic}

Generated: {datetime.datetime.utcnow().isoformat()}Z

## Files
- INDEX.md (human index)
- documents.json (structured export)

## How to sell
- Bundle these into a ZIP.
- Add a LICENSE.md (use licensing_matrix_generator + licensing_stamper).
- Create platform packs (platform_packs) + storefront (storefront_html_generator).
"""
        write_text(out_dir / "README.md", readme)

        # Zip the pack for convenience
        bundle_files = [out_dir / "INDEX.md", out_dir / "documents.json", out_dir / "README.md"]
        bundle_zip = package_bundle(f"reference_pack__{slug}", bundle_files)
        return ModuleResult(
            artifact_paths=[str(p) for p in bundle_files] + [str(bundle_zip)],
            metadata={"doc_count": len(docs_export), "bundle_zip": str(bundle_zip)}
        )
