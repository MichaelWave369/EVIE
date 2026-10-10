"""R13 worker: exactly one disposable CAD generation, never a generic workflow executor.

Called only as an isolated Python process with a temporary working directory.
Emits sanitized base64 *artifact bytes*, not filesystem paths or credentials.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

WORKFLOW = "openblueprint_concept_floor_plan"
MODULE = "openblueprint_floor_plan"
FIXTURE = {
    "topic": "EVIE Supervised Concept",
    "constraints": {
        "units": "ft", "width": 24, "depth": 16,
        "partition": "vertical", "include_door": True,
        "include_network": True,
    },
}
MAX_ARTIFACT_BYTES = 64_000


def generate_fixed_artifact() -> dict:
    from app.modules.openblueprint_floor_plan import OpenBlueprintFloorPlanModule
    from app.family_gate.openblue_preflight import inspect_openblue_bytes

    root = Path.cwd().resolve()
    module = OpenBlueprintFloorPlanModule()
    module.artifact_root = lambda slug, namespace: root / "artifacts" / namespace / slug
    output = module.generate(FIXTURE["topic"], dict(FIXTURE["constraints"]))
    paths = [Path(item) for item in output.artifact_paths]
    if len(paths) != 2:
        raise ValueError("unexpected producer artifact count")
    expected = ("openblueprint.evie-proposal.json", "sha256-receipt.json")
    if tuple(p.name for p in paths) != expected:
        raise ValueError("unexpected generated artifacts")
    if any(not p.resolve().is_relative_to(root) or not p.is_file() or p.is_symlink()
           or p.stat().st_size > MAX_ARTIFACT_BYTES for p in paths):
        raise ValueError("artifact path, kind or size invalid")
    artifact = paths[0].read_bytes()
    verification = inspect_openblue_bytes(artifact)
    package = json.loads(artifact)
    receipt = json.loads(paths[1].read_text(encoding="utf-8"))
    digest = hashlib.sha256(artifact).hexdigest()
    if (verification["walls"] != 5 or verification["symbols"] != 2
            or verification["units"] != "ft" or verification["sourceMode"] != "generated"):
        raise ValueError("unexpected generated shape")
    project = package["project"]
    expected_walls = (
        (0, 0, 24, 0), (24, 0, 24, 16), (24, 16, 0, 16),
        (0, 16, 0, 0), (12, 0, 12, 16),
    )
    if tuple(tuple(w[k] for k in ("x1", "y1", "x2", "y2")) for w in project["walls"]) != expected_walls:
        raise ValueError("unexpected wall geometry")
    if {s["type"] for s in project["symbols"]} != {"door", "network"}:
        raise ValueError("missing expected fixture symbols")
    run_id = package["source"]["runId"]
    if receipt.get("runId") != run_id or receipt.get("sha256") != digest:
        raise ValueError("producer digest receipt mismatch")
    return {
        "schemaVersion": "evie.supervised-worker-output/1",
        "workflow": WORKFLOW,
        "module": MODULE,
        "artifactBase64": base64.b64encode(artifact).decode("ascii"),
        "sha256": digest,
        "sourceRunId": run_id,
        "walls": 5,
        "symbols": 2,
        "units": "ft",
    }


def main() -> int:
    try:
        print(json.dumps(generate_fixed_artifact(), separators=(",", ":")))
        return 0
    except Exception as exc:
        # Never echo dynamic exception messages or local filesystem paths.
        print(json.dumps({
            "schemaVersion": "evie.supervised-worker-output/1",
            "status": "failed",
            "errorType": type(exc).__name__,
        }))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
