"""Offline EVIE diagnostic and opt-in disposable floor-plan smoke test."""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from app.modules import REGISTRY
from app.security.auth import api_key_is_configured
from app.settings import settings

ROOT = Path(__file__).resolve().parents[1]

def check_workflow_references(workflows: dict[str, Any], modules: set[str]) -> list[str]:
    errors = []
    for name, flow in workflows.items():
        if not isinstance(flow, dict) or not isinstance(flow.get("steps"), list):
            errors.append(f"{name}: invalid steps")
            continue
        for index, step in enumerate(flow["steps"]):
            if not isinstance(step, dict):
                errors.append(f"{name}: step {index} invalid")
                continue
            module = step.get("module")
            nested = step.get("workflow")
            if isinstance(module, str) and module.startswith("workflow:"):
                nested, module = module[len("workflow:"):], None
            if module and module not in modules:
                errors.append(f"{name}: unregistered module {module}")
            if nested and nested not in workflows:
                errors.append(f"{name}: missing workflow {nested}")
            if not module and not nested:
                errors.append(f"{name}: empty step {index}")
    return errors

def smoke_cad() -> dict[str, Any]:
    """Run only the deterministic local CAD producer, entirely in a temp directory."""
    from app.modules.openblueprint_floor_plan import OpenBlueprintFloorPlanModule
    module = OpenBlueprintFloorPlanModule()
    with tempfile.TemporaryDirectory(prefix="evie-r5-") as temp:
        root = Path(temp).resolve()
        module.artifact_root = lambda slug, namespace: root / namespace / slug
        generated = module.generate("EVIE Revival Test", {"width": 24, "depth": 16, "partition": "vertical"})
        if len(generated.artifact_paths) != 2:
            raise ValueError("expected proposal and digest receipt")
        a, b = [Path(x).resolve() for x in generated.artifact_paths]
        if not (a.is_relative_to(root) and b.is_relative_to(root)):
            raise ValueError("smoke output escaped temporary root")
        data = a.read_bytes()
        proposal = json.loads(data)
        receipt = json.loads(b.read_text(encoding="utf-8"))
        if (proposal.get("schemaVersion") != "openblueprint.evie-proposal/1" or
            proposal.get("source", {}).get("mode") != "generated" or
            proposal.get("project", {}).get("schemaVersion") != "openblueprint.project/1" or
            receipt.get("sha256") != hashlib.sha256(data).hexdigest()):
            raise ValueError("producer schema/digest verification failed")
        return {"status": "pass", "producer": "openblueprint_floor_plan",
                "walls": len(proposal["project"]["walls"]), "symbols": len(proposal["project"]["symbols"]),
                "digest_verified": True, "persistent_artifacts": False}

def inspect(include_cad_smoke: bool = False) -> dict[str, Any]:
    workflows = json.loads((ROOT / "configs" / "workflows.json").read_text(encoding="utf-8"))
    modules = sorted(REGISTRY)
    errors = check_workflow_references(workflows, set(modules))
    key = settings.api_key
    has_key = api_key_is_configured(key)
    result = {
        "schemaVersion": "evie.revival-doctor/1",
        "scope": "registered source, not live module/provider availability",
        "modules": {"registered_count": len(modules), "names": modules, "execution_verified": False},
        "workflows": {"configured_count": len(workflows), "names": sorted(workflows),
                      "broken_references": errors, "execution_verified": False},
        "security": {"api_key_configured": has_key, "api_key_is_short": bool(has_key and len(key) < 24),
                     "local_api_only": True, "public_github_pages_is_not_runtime": True},
        "cad_smoke": {"status": "not_run"},
    }
    if include_cad_smoke:
        try:
            result["cad_smoke"] = smoke_cad()
        except Exception as exc:
            result["cad_smoke"] = {"status": "fail", "reason": type(exc).__name__}
    result["overall"] = ("fail" if errors or not has_key or result["cad_smoke"]["status"] == "fail"
                         else "pass" if result["cad_smoke"]["status"] == "pass" else "inventory_only")
    return result

def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose the local EVIE runtime; no keys or files are uploaded.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--smoke-cad", action="store_true", help="run a single bounded CAD module in a disposable temp directory")
    args = parser.parse_args()
    result = inspect(include_cad_smoke=args.smoke_cad)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("EVIE modules:", result["modules"]["registered_count"])
        print("EVIE workflows:", result["workflows"]["configured_count"])
        print("Broken workflow references:", len(result["workflows"]["broken_references"]))
        print("Configured API key:", result["security"]["api_key_configured"])
        print("Disposable CAD smoke:", result["cad_smoke"]["status"])
        print("Result:", result["overall"])
    return 1 if result["overall"] == "fail" else 0

if __name__ == "__main__":
    raise SystemExit(main())
