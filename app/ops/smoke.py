from __future__ import annotations

from typing import Any

from app.modules import REGISTRY
from app.workflows import runner


SMOKE_MODULE_TARGETS = [
    "trend_surfer",
    "idea_miner",
    "sales_page_builder",
    "email_sequence_builder",
    "image_generator_v2",
    "thumbnail_generator",
]

SMOKE_WORKFLOW_TARGETS = [
    "vault_to_money_publish",
    "vault_to_membership_pack",
    "trend_to_money_publish",
]


def run_smoke_tests(topic: str = "EVIE Smoke Topic") -> dict[str, Any]:
    results: list[dict[str, Any]] = []

    for name in SMOKE_MODULE_TARGETS:
        if name not in REGISTRY:
            results.append({"target": name, "type": "module", "status": "fail", "message": "module not registered"})
            continue
        try:
            mod = REGISTRY[name]
            constraints = {"use_api_fallback": False, "num_images": 1, "num_variants": 1}
            res = mod.generate(topic, constraints)
            status = "pass" if isinstance(getattr(res, "artifact_paths", []), list) else "warn"
            results.append({"target": name, "type": "module", "status": status, "artifacts": len(getattr(res, "artifact_paths", []) or [])})
        except Exception as e:
            results.append({"target": name, "type": "module", "status": "fail", "message": str(e)})

    for wf in SMOKE_WORKFLOW_TARGETS:
        try:
            out = runner.run_workflow(wf, topic=topic, constraints={"dry_run": True}, dry_run=True)
            ok = bool(out.get("steps"))
            results.append({"target": wf, "type": "workflow", "status": "pass" if ok else "warn", "steps": len(out.get("steps") or [])})
        except Exception as e:
            results.append({"target": wf, "type": "workflow", "status": "fail", "message": str(e)})

    has_fail = any(r.get("status") == "fail" for r in results)
    has_warn = any(r.get("status") == "warn" for r in results)
    overall = "fail" if has_fail else ("warn" if has_warn else "pass")
    return {"overall": overall, "results": results}
