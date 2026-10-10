"""Read-only EVIE workflow planner. NO workflow runner, DB, module imports or secrets.

Plans are advisory source snapshots, never grants. Unlike run_workflow(dry_run=True),
this module does not create a run record, query providers, or invoke module.generate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_SOURCE = ROOT / "app" / "modules" / "__init__.py"
WORKFLOW_SOURCE = ROOT / "configs" / "workflows.json"
SCHEMA = "evie.workflow-preflight/1"
MAX_DEPTH = 12
MAX_STEPS = 128
RISK_RE = re.compile(r"publish|upload|gumroad|payhip|launch|scheduler|automation|execute|bridge|comfyui")

def read_source() -> tuple[dict, set[str], str]:
    source = REGISTRY_SOURCE.read_text(encoding="utf-8")
    marker = source.split("\nREGISTRY = {", 1)
    if len(marker) != 2:
        raise ValueError("EVIE registry marker not found")
    body = marker[1].split("\n}", 1)[0]
    entries = re.findall(r'^\s*"([a-z0-9_]+)"\s*:\s*([A-Za-z_]\w*)\(\s*\),\s*$', body, re.M)
    if len(entries) != len(re.findall(r'^\s*"([a-z0-9_]+)"\s*:', body, re.M)):
        raise ValueError("unrecognized EVIE registry line")
    module_names = {key for key, _ in entries}
    if len(module_names) != len(entries):
        raise ValueError("duplicate EVIE registry keys")
    raw = WORKFLOW_SOURCE.read_text(encoding="utf-8")
    workflows = json.loads(raw)
    if not isinstance(workflows, dict):
        raise ValueError("invalid workflow registry")
    digest = hashlib.sha256((source + "\n--- workflow ---\n" + raw).encode("utf-8")).hexdigest()
    return workflows, module_names, digest

def reachable_flags(workflows: dict, start: str) -> list[str]:
    if start not in workflows:
        raise ValueError("unknown EVIE workflow")
    found: set[str] = set()
    visited: set[str] = set()
    def visit(name: str, stack: tuple[str, ...]) -> None:
        if name in stack:
            raise ValueError("nested workflow cycle detected")
        if name in visited:
            return
        visited.add(name)
        for step in workflows[name]["steps"]:
            if not isinstance(step, dict):
                raise ValueError("workflow step malformed")
            flag = step.get("when_constraint")
            if flag:
                if not isinstance(flag, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", flag):
                    raise ValueError("invalid constraint flag")
                found.add(flag)
            sub = step.get("workflow")
            if sub:
                if sub not in workflows:
                    raise ValueError("missing nested workflow")
                visit(sub, stack + (name,))
    visit(start, ())
    return sorted(found)

def plan_workflow(
    name: str, *,
    workflows: dict[str, Any], modules: set[str], source_digest: str,
    enabled_flags: list[str] | None = None,
) -> dict[str, Any]:
    if name not in workflows:
        raise ValueError("unknown workflow")
    allowed = set(reachable_flags(workflows, name))
    flags = enabled_flags or []
    if not isinstance(flags, list) or any(not isinstance(flag, str) for flag in flags):
        raise ValueError("invalid flags")
    if len(set(flags)) != len(flags) or any(flag not in allowed for flag in flags):
        raise ValueError("unknown/duplicate optional constraint")
    active = set(flags)
    rows: list[dict[str, Any]] = []
    problems: list[str] = []
    def walk(current: str, lineage: tuple[str, ...]) -> None:
        if current in lineage or len(lineage) >= MAX_DEPTH:
            raise ValueError("nested workflow cycle/depth limit")
        for index, step in enumerate(workflows[current]["steps"], start=1):
            if len(rows) >= MAX_STEPS:
                raise ValueError("workflow plan exceeds 128 rows")
            if not isinstance(step, dict):
                raise ValueError("invalid workflow step")
            flag = step.get("when_constraint")
            selected = not flag or flag in active
            target = step.get("workflow")
            mod = step.get("module")
            if bool(target) == bool(mod):
                raise ValueError("ambiguous workflow step")
            if target and target not in workflows:
                problems.append("unknown nested workflow")
            if mod and mod not in modules:
                problems.append("unregistered module")
            record = {
                "path": "/".join([*lineage, current, str(index)]),
                "workflow": current,
                "index": index,
                "kind": "nested" if target else "module",
                "name": target or mod,
                "optional": step.get("optional") is True,
                "condition": flag,
                "decision": "candidate_only" if selected else "skipped_by_default",
                "effectReview": bool(mod and RISK_RE.search(mod)),
                "executionAuthorized": False,
                "executed": False,
            }
            rows.append(record)
            if selected and target and target in workflows:
                walk(target, (*lineage, current))
    walk(name, ())
    count = sum(r["kind"] == "module" and r["decision"] == "candidate_only" for r in rows)
    risky = sum(r["effectReview"] and r["decision"] == "candidate_only" for r in rows)
    return {
        "schemaVersion": SCHEMA,
        "workflow": name,
        "sourceSha256": source_digest,
        "enabledFlags": sorted(active),
        "availableFlags": sorted(allowed),
        "steps": rows,
        "summary": {
            "planRows": len(rows),
            "candidateModules": count,
            "effectReviewCandidates": risky,
            "skippedRows": sum(r["decision"] == "skipped_by_default" for r in rows),
            "registryProblems": problems,
        },
        "evidence": "source-plan-only",
        "databaseTouched": False,
        "executionAuthorized": False,
        "executed": False,
        "providerAvailabilityVerified": False,
        "note": "Read-only plan from checked-in source. No modules, providers, DB or nested runners invoked.",
    }

def main() -> int:
    parser = argparse.ArgumentParser(description="Offline EVIE workflow plan, no run records or execution.")
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--enable", action="append", default=[], help="opt in to an existing when_constraint flag")
    args = parser.parse_args()
    try:
        workflows, modules, digest = read_source()
        report = plan_workflow(args.workflow, workflows=workflows, modules=modules,
                               source_digest=digest, enabled_flags=args.enable)
        print(json.dumps(report, indent=2))
        return 1 if report["summary"]["registryProblems"] else 0
    except (ValueError, KeyError, OSError, json.JSONDecodeError):
        print(json.dumps({"schemaVersion": SCHEMA, "status": "invalid-plan",
                          "executionAuthorized": False, "databaseTouched": False}))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
