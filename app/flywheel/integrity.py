
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List, Tuple
import hashlib, datetime, json

from app.db import queries
from app.export.packager import write_text

def sha256_file(path: Path) -> Tuple[str, int]:
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
            size += len(b)
    return h.hexdigest(), size

def record_and_report(sku: str, version: str, artifact_paths: List[str], report_dir: Path) -> Dict[str, Any]:
    report_dir.mkdir(parents=True, exist_ok=True)
    paths = [Path(p) for p in artifact_paths if p]
    # compute hashes
    by_hash: Dict[str, List[Path]] = {}
    file_rows = []
    for p in paths:
        if not p.exists() or not p.is_file():
            continue
        sha, size = sha256_file(p)
        by_hash.setdefault(sha, []).append(p)
        file_rows.append({"path": str(p), "sha256": sha, "size_bytes": size})
        try:
            queries.add_fingerprint(sku, version, str(p), sha, size)
        except Exception:
            # fingerprints are best-effort; do not fail the build
            pass

    duplicates_within = {sha: [str(x) for x in ps] for sha, ps in by_hash.items() if len(ps) > 1}

    dup_same_sku = {}
    dup_other_sku = {}
    for sha, ps in by_hash.items():
        hits = queries.find_by_sha(sha, limit=25)
        # current run will also be in hits; ignore exact same sku+version+paths
        same_sku_hits = [h for h in hits if (h.get("sku") == sku and h.get("version") != version)]
        other_sku_hits = [h for h in hits if (h.get("sku") != sku)]
        if same_sku_hits:
            dup_same_sku[sha] = same_sku_hits
        if other_sku_hits:
            dup_other_sku[sha] = other_sku_hits

    # Write report
    ts = datetime.datetime.utcnow().isoformat() + "Z"
    lines = []
    lines.append(f"# Bundle Integrity Report\n\nSKU: **{sku}**\nVersion: **{version}**\nGenerated: {ts}\n")
    lines.append("## Files\n")
    for r in file_rows[:369]:  # keep it bounded
        lines.append(f"- {r['path']}  \n  sha256: `{r['sha256']}`  \n  size: {r['size_bytes']} bytes")
    lines.append("\n## Duplicate Checks\n")
    if duplicates_within:
        lines.append("### Duplicates *within* this bundle\n")
        for sha, ps in duplicates_within.items():
            lines.append(f"- `{sha}`\n  - " + "\n  - ".join(ps))
    else:
        lines.append("- No duplicates found within this bundle.")
    if dup_same_sku:
        lines.append("\n### Reused content (same SKU, older versions)\n")
        for sha, hits in dup_same_sku.items():
            lines.append(f"- `{sha}` seen in:")
            for h in hits[:9]:
                lines.append(f"  - {h.get('version')} — {h.get('path')}")
    if dup_other_sku:
        lines.append("\n### Reused content (across other SKUs)\n")
        for sha, hits in dup_other_sku.items():
            lines.append(f"- `{sha}` seen in:")
            for h in hits[:9]:
                lines.append(f"  - {h.get('sku')} {h.get('version')} — {h.get('path')}")
    if not dup_same_sku and not dup_other_sku:
        lines.append("\n- No reuse detected against prior fingerprints.")

    report_path = report_dir / "DUPLICATES_REPORT.md"
    write_text(report_path, "\n".join(lines))

    return {
        "report_path": str(report_path),
        "duplicates_within": duplicates_within,
        "dup_same_sku": {k: v[:5] for k,v in dup_same_sku.items()},
        "dup_other_sku": {k: v[:5] for k,v in dup_other_sku.items()},
        "file_count": len(file_rows),
    }
