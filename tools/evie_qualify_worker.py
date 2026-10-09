"""Fixed-scenario EVIE qualification worker. Invoked only by allowlisted local CLI."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path

SCENARIO = "cad_rectangular_concept_v1"
MODULE = "openblueprint_floor_plan"

def qualify() -> dict:
    from app.modules.openblueprint_floor_plan import OpenBlueprintFloorPlanModule
    root = Path.cwd().resolve()
    module = OpenBlueprintFloorPlanModule()
    module.artifact_root = lambda slug, namespace: root / "artifacts" / namespace / slug
    result = module.generate("Qualification Fixture", {
        "units": "ft", "width": 24, "depth": 16,
        "partition": "vertical", "include_door": True, "include_network": True
    })
    paths = [Path(p).resolve() for p in result.artifact_paths]
    if len(paths) != 2 or any(not p.is_relative_to(root) for p in paths):
        raise ValueError("artifact count or containment failed")
    if paths[0].name != "openblueprint.evie-proposal.json" or paths[1].name != "sha256-receipt.json":
        raise ValueError("unexpected artifact type")
    if any(p.is_symlink() or p.stat().st_size > 100_000 for p in paths):
        raise ValueError("unsafe or oversized artifact")
    proposal_bytes = paths[0].read_bytes()
    package = json.loads(proposal_bytes)
    receipt = json.loads(paths[1].read_text(encoding="utf-8"))
    project = package["project"]
    walls = project["walls"]
    symbols = project["symbols"]
    ids = [obj["id"] for obj in walls + symbols]
    expected_walls = [(0, 0, 24, 0), (24, 0, 24, 16), (24, 16, 0, 16),
                      (0, 16, 0, 0), (12, 0, 12, 16)]
    walls_ok = len(walls) == 5 and all(
        tuple(w[k] for k in ("x1", "y1", "x2", "y2")) == expected_walls[index]
        and math.isfinite(w["height"]) and math.isfinite(w["thickness"])
        and w["height"] > 0 and w["thickness"] > 0
        for index, w in enumerate(walls)
    )
    checks = {
        "versioned_proposal": package.get("schemaVersion") == "openblueprint.evie-proposal/1",
        "versioned_project": project.get("schemaVersion") == "openblueprint.project/1",
        "bounded_wall_geometry": walls_ok,
        "symbol_types": len(symbols) == 2 and {s["type"] for s in symbols} == {"door", "network"},
        "unique_element_ids": len(ids) == len(set(ids)),
        "source_labels": package["source"]["system"] == "EVIE" and
                         package["source"]["cardId"] == MODULE and package["source"]["mode"] == "generated",
        "run_id_bound": receipt.get("runId") == package["source"]["runId"],
        "digest_match": receipt.get("sha256") == hashlib.sha256(proposal_bytes).hexdigest(),
        "artifact_scope": all(p.is_relative_to(root) for p in paths),
    }
    source_path = Path(__file__).resolve().parents[1] / "app" / "modules" / "openblueprint_floor_plan.py"
    return {
        "schemaVersion": "evie.qualification-observation/1",
        "module": MODULE,
        "scenario": SCENARIO,
        "checks": checks,
        "sourceSha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "artifactSha256": hashlib.sha256(proposal_bytes).hexdigest(),
        "observedWalls": len(walls),
        "observedSymbols": len(symbols),
    }

def main() -> int:
    try:
        outcome = qualify()
        outcome["status"] = "pass" if all(outcome["checks"].values()) else "fail"
        print(json.dumps(outcome, sort_keys=True))
        return 0 if outcome["status"] == "pass" else 1
    except Exception as exc:
        # The receipt must never include arbitrary exception text or private paths.
        print(json.dumps({"schemaVersion": "evie.qualification-observation/1",
                          "module": MODULE, "scenario": SCENARIO,
                          "status": "fail", "errorType": type(exc).__name__}))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
