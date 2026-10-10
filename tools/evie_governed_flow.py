"""R18: two-stage supervised local workflow coordinator with an immutable event trail.

Real R14 nine-hook output pauses for operator review; only a separate, signed,
short-lived R16 lease can resume stage 2 in the R17 offline Docker capsule.
There is NO automatic signing, external publishing, background queue, generic
module dispatcher, or host-Python fallback for the second stage.

This is local operator coordination, not an authenticated multiuser scheduler.
Event files are create-exclusive self-reports, not tamper-proof attestations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

from app.workflows.preflight import ROOT
from tools import evie_supervised_hooks as hooks
from tools import evie_supervised_distribution as distribution
from tools import evie_isolated_distribution as isolated
from tools import evie_container_runner as capsule
from tools import evie_hooks_container as hooks_capsule
from tools.evie_action_lease_contract import load_lease, verify_local_lease
from tools.evie_attest import load_public_key
from tools.evie_supervised import _stage_directory, _write_new

SCHEMA = "evie.governed-content-flow/1"
FLOW = "local_hooks_to_distribution_review"
STATES = ("paused_for_human_review", "resume_attempt_recorded", "distribution_staged_for_review")
EVENT_1 = "01-hooks-paused.json"
EVENT_2 = "02-signed-resume-attempt.json"
EVENT_3 = "03-distribution-staged.json"
MAX_EVENT_SIZE = 8192


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_file(path: Path, *, limit: int = MAX_EVENT_SIZE) -> dict:
    if not path.is_file() or path.is_symlink() or not 0 < path.stat().st_size <= limit:
        raise ValueError("missing, symlinked or oversized local event file")
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("local event must be JSON object")
    return obj


def _emit(directory: Path, filename: str, record: dict) -> None:
    encoded = (json.dumps(record, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    if len(encoded) > MAX_EVENT_SIZE:
        raise ValueError("event exceeds bounded size")
    _write_new(directory / filename, encoded)


def _session_root(path: str) -> Path:
    folder = Path(path).expanduser().absolute()
    if (not folder.is_dir() or folder.is_symlink()
            or folder.resolve().is_relative_to(ROOT.resolve())):
        raise ValueError("expected existing non-symlink session outside the source checkout")
    return folder


def _preflight() -> tuple[dict, str]:
    plan, digest, _ = distribution._source_check()
    if (len(plan["steps"]) != 2
            or [r["name"] for r in plan["steps"]]
            != ["hooks_generator", "distribution_generator"]
            or plan["executionAuthorized"] is not False
            or plan["executed"] is not False):
        raise ValueError("R18 fixed two-stage source plan drift")
    return plan, digest


def plan() -> dict:
    reviewed, digest = _preflight()
    return {
        "schemaVersion": SCHEMA,
        "state": "plan_only",
        "workflow": FLOW,
        "sourceSha256": digest,
        "steps": [r["name"] for r in reviewed["steps"]],
        "runCapability": "local-explicit-two-stage-only",
        "approvalBoundary": "human_review_then_independent_short_lived_signed_lease",
        "stageOneIsolation": "offline-Docker-required-no-host-fallback",
        "stageTwoIsolation": "offline-Docker-required-no-host-fallback",
        "nextStageExecuted": False,
        "publishingAuthorized": False,
        "note": "Source-only plan; no file writes or worker calls.",
    }


def start_session(*, session_dir: str, script_file: str,
                  topic: str, confirm: bool, timeout: int = 20) -> dict:
    """One explicit R14 host-local draft run; stop, no signatures and no stage 2."""
    if confirm is not True:
        raise ValueError("explicit --confirm-local-execution required for stage 1")
    if type(timeout) is not int or not 1 <= timeout <= 20:
        raise ValueError("stage 1 wall time above audited maximum")
    target = _stage_directory(session_dir)
    _, digest = _preflight()
    # Docker is mandatory for the NEW controller's Stage 1.
    # Check preinstalled image BEFORE creating the session directory.
    image_id = hooks_capsule.image_preflight()
    def fixed_worker(title: str, script: str, seconds: int) -> dict:
        return hooks_capsule.run_hooks_isolated(title, script, seconds, image_id=image_id)
    isolation = hooks_capsule.isolation_metadata(image_id)
    # Validate operator input before allocating session.
    hooks._title(topic) if hasattr(hooks, "_title") else None
    hooks.read_input(script_file)
    target.mkdir(mode=0o700, exist_ok=False)
    try:
        stage1 = hooks.stage_hooks(
            script_file=script_file, topic=topic,
            stage_dir=str(target / "hooks"),
            confirm=True, timeout=timeout,
            worker_backend=fixed_worker, isolation_metadata=isolation,
        )
        if stage1.get("executionIsolation") != isolation:
            raise ValueError("Stage 1 isolation evidence not attached")
        if stage1.get("workflowSourceSha256") != digest:
            raise ValueError("R14 source drift while preparing controller session")
        record = {
            "schemaVersion": SCHEMA,
            "event": "hooks_staged",
            "state": STATES[0],
            "workflow": FLOW,
            "sessionNonce": secrets.token_hex(16),
            "createdAt": _utc(),
            "workflowSourceSha256": digest,
            "hooksArtifactSha256": stage1["artifactSha256"],
            "topic": stage1["topic"],
            "hooksStage": "hooks",
            "nextStage": "distribution",
            "stageOneExecutedLocally": True,
            "stageOneOSIsolated": True,
            "stageOneIsolation": isolation,
            "stageTwoExecuted": False,
            "signedApprovalReceived": False,
            "externalPublishingAuthorized": False,
            "editorialApprovalGranted": False,
        }
        _emit(target, EVENT_1, record)
        return record
    except BaseException:
        # Preserve possible evidence rather than deleting a partially staged run.
        # Subsequent calls cannot adopt a half-complete session.
        raise


def _read_session(session_dir: str) -> tuple[Path, dict, str]:
    folder = _session_root(session_dir)
    first = _json_file(folder / EVENT_1)
    if (first.get("schemaVersion") != SCHEMA or first.get("event") != "hooks_staged"
            or first.get("state") != STATES[0] or first.get("workflow") != FLOW
            or not isinstance(first.get("sessionNonce"), str)
            or len(first["sessionNonce"]) != 32
            or first.get("hooksStage") != "hooks"
            or first.get("nextStage") != "distribution"
            or first.get("stageOneExecutedLocally") is not True
            or first.get("stageTwoExecuted") is not False
            or first.get("signedApprovalReceived") is not False
            or first.get("externalPublishingAuthorized") is not False):
        raise ValueError("unsupported stage-one session event")
    _, source = _preflight()
    if first.get("workflowSourceSha256") != source:
        raise ValueError("session source revision changed")
    distribution._load_approved_first_stage(
        str(folder / "hooks"), first.get("hooksArtifactSha256"), source,
    )
    receipt = _json_file(folder / "hooks" / "review-receipt.json", limit=32_000)
    if receipt.get("topic") != first.get("topic"):
        raise ValueError("session topic and original receipt mismatch")
    if (folder / EVENT_3).exists() and not (folder / EVENT_2).exists():
        raise ValueError("unsequenced stage-two event")
    return folder, first, source


def session_status(session_dir: str) -> dict:
    """Read-only inspection. Do not open Docker or spend nonce."""
    folder, first, _ = _read_session(session_dir)
    attempt_path, completed_path = folder / EVENT_2, folder / EVENT_3
    if not attempt_path.exists():
        state = STATES[0]
    elif not completed_path.exists():
        _validate_attempt(first, _json_file(attempt_path))
        state = STATES[1]
    else:
        attempt = _json_file(attempt_path)
        _validate_attempt(first, attempt)
        finished = _json_file(completed_path)
        if (finished.get("schemaVersion") != SCHEMA
                or finished.get("state") != STATES[2]
                or finished.get("event") != "distribution_staged"
                or finished.get("sessionNonce") != first["sessionNonce"]
                or finished.get("approvedHooksSha256") != first["hooksArtifactSha256"]
                or finished.get("leaseNonce") != attempt["leaseNonce"]):
            raise ValueError("invalid completed-stage event")
        output = folder / "distribution" / "distribution-draft.json"
        if (not output.is_file() or output.is_symlink()
                or output.stat().st_size > 32768
                or hashlib.sha256(output.read_bytes()).hexdigest()
                != finished.get("distributionSha256")):
            raise ValueError("staged distribution output changed or is missing")
        state = STATES[2]
    return {
        "schemaVersion": SCHEMA,
        "state": state,
        "workflow": FLOW,
        "hooksArtifactSha256": first["hooksArtifactSha256"],
        "workflowSourceSha256": first["workflowSourceSha256"],
        "sessionNonce": first["sessionNonce"],
        "stageOneIsolation": first.get("stageOneIsolation", {"profile": "legacy-host-subprocess"}),
        "stageOneOutput": "hooks/nine-hooks.json",
        "stageTwoOutput": "distribution/distribution-draft.json" if state == STATES[2] else None,
        "signedLeaseNecessary": state == STATES[0],
        "mayAutomaticallyResume": False,
        "publishingAuthorized": False,
        "editorialApprovalGranted": False,
        "note": ("If a resume attempt has been recorded but no final event exists, "
                 "the outcome is unknown. Never auto-retry this session."),
    }


def _validate_attempt(first: dict, attempt: dict) -> None:
    if (attempt.get("schemaVersion") != SCHEMA
            or attempt.get("event") != "signed_resume_attempt"
            or attempt.get("state") != STATES[1]
            or attempt.get("sessionNonce") != first["sessionNonce"]
            or attempt.get("approvedHooksSha256") != first["hooksArtifactSha256"]
            or attempt.get("stageTwoExecutionAttempted") is not True
            or attempt.get("externalPublishingAuthorized") is not False
            or attempt.get("editorialApprovalGranted") is not False):
        raise ValueError("unsupported signed resume attempt event")


def resume_session(*, session_dir: str, lease_file: str,
                   trusted_public: str, ledger: str,
                   confirm: bool, timeout: int = 20) -> dict:
    """One manually confirmed, signed R17 offline Docker attempt, with no retries."""
    if confirm is not True:
        raise ValueError("explicit human confirmation required to resume")
    if type(timeout) is not int or not 1 <= timeout <= 20:
        raise ValueError("resume timeout outside signed budget")
    folder, first, source = _read_session(session_dir)
    # Preserve status visibility for old R18 sessions but never approve an old
    # host-executed Stage 1 for the R19 isolated-controller lane.
    if (first.get("stageOneOSIsolated") is not True
            or first.get("stageOneIsolation", {}).get("profile") != hooks_capsule.PROFILE
            or first["stageOneIsolation"].get("networkMode") != "none"):
        raise ValueError("Stage 1 requires a verified local Docker capsule profile")
    if (folder / EVENT_2).exists() or (folder / EVENT_3).exists():
        raise ValueError("session already attempted; no resume/replay")
    stage = str(folder / "distribution")
    _stage_directory(stage)
    key = load_public_key(trusted_public)
    body = verify_local_lease(
        load_lease(lease_file), key, artifact_sha=first["hooksArtifactSha256"],
        source_sha=source, stage_dir=stage,
    )
    if timeout > body["limits"]["maxWallSeconds"]:
        raise ValueError("runtime exceeds approved signed lease")
    # Fail CLOSED before writing the attempt event or spending the lease if
    # Docker is unavailable. run_isolated_with_lease checks again before burn.
    capsule.image_preflight()
    attempt = {
        "schemaVersion": SCHEMA,
        "event": "signed_resume_attempt", "state": STATES[1],
        "sessionNonce": first["sessionNonce"],
        "leaseNonce": body["nonce"],
        "approvedHooksSha256": first["hooksArtifactSha256"],
        "attemptedAt": _utc(),
        "requestedTimeoutSeconds": timeout,
        "stageTwoExecutionAttempted": True,
        "externalPublishingAuthorized": False,
        "editorialApprovalGranted": False,
        "outcomeKnown": False,
    }
    # Atomic exclusive create blocks a concurrent second resume against this
    # session, even if both processes raced while verifying the signed lease.
    _emit(folder, EVENT_2, attempt)
    observation = isolated.run_isolated_with_lease(
        hooks_dir=str(folder / "hooks"),
        approved_hooks_sha256=first["hooksArtifactSha256"],
        stage_dir=stage,
        lease_file=lease_file, trusted_public=trusted_public, ledger=ledger,
        confirm=True, timeout=timeout,
    )
    result = {
        "schemaVersion": SCHEMA,
        "event": "distribution_staged", "state": STATES[2],
        "sessionNonce": first["sessionNonce"],
        "leaseNonce": body["nonce"],
        "approvedHooksSha256": first["hooksArtifactSha256"],
        "distributionSha256": observation["distributionSha256"],
        "stagedAt": _utc(),
        "signedLeaseVerifiedByRunner": observation["approvalSignatureVerified"] is True,
        "dockerProfile": observation["containerIsolation"].get("profile"),
        "stageTwoExecutedLocally": True,
        "externalPublishingAuthorized": False,
        "editorialApprovalGranted": False,
        "finalDone": False,
    }
    if (not result["signedLeaseVerifiedByRunner"]
            or result["dockerProfile"] != capsule.PROFILE):
        raise ValueError("isolated second-stage observation not recognized")
    _emit(folder, EVENT_3, result)
    return result


def main() -> int:
    p = argparse.ArgumentParser(description="EVIE governed two-stage local content run, human-pause and signed offline Docker resume")
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("plan")
    s = sub.add_parser("start")
    s.add_argument("--session-dir", required=True)
    s.add_argument("--script-file", required=True)
    s.add_argument("--topic", required=True)
    s.add_argument("--confirm-local-execution", action="store_true")
    s.add_argument("--timeout", type=int, default=20)
    q = sub.add_parser("status")
    q.add_argument("--session-dir", required=True)
    r = sub.add_parser("resume")
    r.add_argument("--session-dir", required=True)
    r.add_argument("--lease-file", required=True)
    r.add_argument("--trusted-public", required=True)
    r.add_argument("--ledger", required=True)
    r.add_argument("--confirm-local-execution", action="store_true")
    r.add_argument("--timeout", type=int, default=20)
    args = p.parse_args()
    try:
        if args.action == "plan":
            result = plan()
        elif args.action == "start":
            result = start_session(session_dir=args.session_dir, script_file=args.script_file,
                                   topic=args.topic, confirm=args.confirm_local_execution,
                                   timeout=args.timeout)
        elif args.action == "status":
            result = session_status(args.session_dir)
        else:
            result = resume_session(session_dir=args.session_dir,
                                    lease_file=args.lease_file,
                                    trusted_public=args.trusted_public,
                                    ledger=args.ledger,
                                    confirm=args.confirm_local_execution,
                                    timeout=args.timeout)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, TypeError, UnicodeError, json.JSONDecodeError):
        print(json.dumps({
            "schemaVersion": SCHEMA, "status": "rejected",
            "reason": "invalid-session-or-approved-operation-failed",
            "publishingAuthorized": False, "automaticRetry": False,
        }))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
