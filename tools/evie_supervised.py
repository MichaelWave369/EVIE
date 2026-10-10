"""R13: explicitly opted-in, single-workflow local CAD execution & review staging.

This is a separate fixed-scenario runner, NOT app.workflows.runner.run_workflow.
No DB, provider credential, imported agent, hosted API, scheduled job or auto-import.
The subprocess is hygiene, NOT an OS network/filesystem sandbox.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from app.family_gate.openblue_preflight import inspect_openblue_bytes
from app.workflows.preflight import read_source, plan_workflow, ROOT
from tools.evie_qualify import SAFE_ENV_KEYS

WORKFLOW = "openblueprint_concept_floor_plan"
MODULE = "openblueprint_floor_plan"
RECEIPT_SCHEMA = "evie.supervised-cad-review/1"
FIXTURE_ID = "cad_supervised_24x16_v1"
MAX_ARTIFACT_BYTES = 64_000
MAX_WORKER_STDOUT_BYTES = 110_000
TIMEOUT_SECONDS = 20


def _check_source() -> tuple[dict, str, str]:
    flows, modules, digest = read_source()
    wf = flows.get(WORKFLOW)
    if not isinstance(wf, dict) or wf.get("steps") != [{"module": MODULE}]:
        raise ValueError("audited workflow steps changed; decline local execution")
    plan = plan_workflow(WORKFLOW, workflows=flows, modules=modules,
                         source_digest=digest, enabled_flags=[])
    if (len(plan["steps"]) != 1 or plan["steps"][0]["name"] != MODULE
            or plan["summary"]["candidateModules"] != 1
            or plan["summary"]["effectReviewCandidates"] != 0
            or plan["summary"]["registryProblems"] or plan["executed"]
            or plan["executionAuthorized"]):
        raise ValueError("R12 source plan failed allowlist gate")
    producer = ROOT / "app/modules/openblueprint_floor_plan.py"
    source_digest = hashlib.sha256(producer.read_bytes()).hexdigest()
    return plan, digest, source_digest


def _run_worker(timeout: int) -> dict:
    env = {key: os.environ[key] for key in SAFE_ENV_KEYS if key in os.environ}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    command = [
        sys.executable, "-I", "-c",
        "import sys;sys.path.insert(0,sys.argv[1]);"
        "from tools.evie_supervised_worker import main;"
        "raise SystemExit(main())",
        str(ROOT),
    ]
    with tempfile.TemporaryDirectory(prefix="evie-supervised-cad-") as temporary:
        job = subprocess.run(command, cwd=temporary, env=env, timeout=timeout,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             check=False)
    if job.returncode != 0 or not 0 < len(job.stdout) <= MAX_WORKER_STDOUT_BYTES:
        raise ValueError("fixed CAD subprocess failed or exceeded output budget")
    raw = json.loads(job.stdout.decode("utf-8"))
    if not isinstance(raw, dict) or raw.get("schemaVersion") != "evie.supervised-worker-output/1":
        raise ValueError("invalid worker protocol")
    return raw


def _validate_output(worker: dict) -> tuple[bytes, dict]:
    if worker.get("workflow") != WORKFLOW or worker.get("module") != MODULE:
        raise ValueError("worker returned a different capability")
    encoded = worker.get("artifactBase64")
    if not isinstance(encoded, str) or len(encoded) > MAX_WORKER_STDOUT_BYTES:
        raise ValueError("worker payload invalid")
    try:
        bytes_out = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("worker artifact encoding invalid") from exc
    if not 0 < len(bytes_out) <= MAX_ARTIFACT_BYTES:
        raise ValueError("artifact outside output budget")
    actual_sha = hashlib.sha256(bytes_out).hexdigest()
    if actual_sha != worker.get("sha256"):
        raise ValueError("worker output digest mismatch")
    detail = inspect_openblue_bytes(bytes_out)
    envelope = json.loads(bytes_out)
    project = envelope["project"]
    expected = (
        (0, 0, 24, 0), (24, 0, 24, 16), (24, 16, 0, 16),
        (0, 16, 0, 0), (12, 0, 12, 16),
    )
    observed = tuple(tuple(w[k] for k in ("x1", "y1", "x2", "y2")) for w in project["walls"])
    if (observed != expected or detail["walls"] != 5 or detail["symbols"] != 2
            or detail["units"] != "ft" or detail["sourceMode"] != "generated"
            or {s["type"] for s in project["symbols"]} != {"door", "network"}
            or worker.get("walls") != 5 or worker.get("symbols") != 2 or worker.get("units") != "ft"
            or not isinstance(worker.get("sourceRunId"), str)
            or not worker["sourceRunId"].startswith("evie-cad-")
            or detail["runId"] != worker["sourceRunId"]):
        raise ValueError("worker output did not match fixed scenario")
    return bytes_out, detail


def _stage_directory(path: str) -> Path:
    if not isinstance(path, str) or not path.strip():
        raise ValueError("explicit new stage directory required")
    stage = Path(path).expanduser()
    if stage.exists() or stage.is_symlink():
        raise ValueError("stage path exists; never overwrite review folders")
    if not stage.parent.is_dir() or stage.parent.is_symlink():
        raise ValueError("stage parent must exist and not be a symlink")
    stage = stage.absolute()
    # Avoid accidentally committing generated data into the public source tree.
    if stage.is_relative_to(ROOT.resolve()):
        raise ValueError("stage outside public EVIE git checkout")
    return stage


def _write_new(path: Path, value: bytes) -> None:
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(value)


def supervised_run(stage_dir: str, *, confirm: bool, workflow: str = WORKFLOW,
                   timeout: int = TIMEOUT_SECONDS) -> dict:
    if confirm is not True:
        raise ValueError("explicit --confirm-local-execution required")
    if workflow != WORKFLOW:
        raise ValueError("workflow is not allowlisted for supervised execution")
    if type(timeout) is not int or not 1 <= timeout <= TIMEOUT_SECONDS:
        raise ValueError("timeout outside audited 1–20 second budget")
    destination = _stage_directory(stage_dir)
    plan, source_sha, producer_sha = _check_source()
    started = time.monotonic()
    observation = _run_worker(timeout)
    data, parsed = _validate_output(observation)
    after_plan, after_source_sha, after_producer_sha = _check_source()
    if after_source_sha != source_sha or after_producer_sha != producer_sha:
        raise ValueError("workflow or producer source changed during execution")
    if after_plan["summary"] != plan["summary"]:
        raise ValueError("source preflight changed during execution")
    sha = hashlib.sha256(data).hexdigest()
    receipt = {
        "schemaVersion": RECEIPT_SCHEMA,
        "status": "staged_for_human_review",
        "workflow": WORKFLOW,
        "module": MODULE,
        "scenario": FIXTURE_ID,
        "origin": "local-unsigned-observation",
        "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "workflowSourceSha256": source_sha,
        "producerSourceSha256": producer_sha,
        "artifactSha256": sha,
        "artifactBytes": len(data),
        "producerRunId": parsed["runId"],
        "walls": parsed["walls"],
        "symbols": parsed["symbols"],
        "units": parsed["units"],
        "durationMs": max(0, round((time.monotonic() - started) * 1000)),
        "limits": {"maxModules": 1, "maxWallSeconds": TIMEOUT_SECONDS,
                   "maxArtifactBytes": MAX_ARTIFACT_BYTES},
        "evidence": {
            "fixedWorkflowStepsMatched": True, "proposalSchemaValidated": True,
            "outputDigestVerified": True, "geometryVerified": True,
        },
        "governance": {
            "localFixtureExecuted": True, "legacyRunnerInvoked": False,
            "databaseTouched": False, "providerCredentialsProvided": False,
            "networkSandboxEnforced": False, "downstreamActionAuthorized": False,
            "recipientAccepted": False, "projectImported": False,
            "humanApprovalRequired": True, "signed": False,
        },
        "note": "Local fixed CAD workflow was staged, not imported into OpenBlue. This is unsigned, self-reported evidence.",
    }
    files = {
        "openblueprint.evie-proposal.json": data,
        "workflow-preflight.json": (json.dumps(plan, indent=2) + "\n").encode("utf-8"),
        "review-receipt.json": (json.dumps(receipt, indent=2) + "\n").encode("utf-8"),
    }
    if sum(map(len, files.values())) > 128_000:
        raise ValueError("review bundle exceeds 128 KB")
    destination.mkdir(mode=0o700, exist_ok=False)
    try:
        for name, contents in files.items():
            _write_new(destination / name, contents)
    except BaseException:
        shutil.rmtree(destination)
        raise
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="Explicit local EVIE CAD run; stages review-only files. No other workflows.")
    sub = parser.add_subparsers(dest="action", required=True)
    run = sub.add_parser("run")
    run.add_argument("workflow", choices=[WORKFLOW])
    run.add_argument("--stage-dir", required=True, help="new review folder OUTSIDE the EVIE checkout")
    run.add_argument("--confirm-local-execution", action="store_true")
    run.add_argument("--timeout", type=int, default=TIMEOUT_SECONDS)
    args = parser.parse_args()
    try:
        receipt = supervised_run(args.stage_dir, confirm=args.confirm_local_execution,
                                 workflow=args.workflow, timeout=args.timeout)
        print(json.dumps(receipt, indent=2))
        return 0
    except (ValueError, OSError, json.JSONDecodeError, UnicodeError, subprocess.TimeoutExpired):
        print(json.dumps({"schemaVersion": RECEIPT_SCHEMA,
                          "status": "failed",
                          "reason": "rejected-or-fixed-run-failed",
                          "downstreamActionAuthorized": False}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
