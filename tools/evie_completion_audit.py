"""R20 read-only completion evidence and source-entrypoint exposure audit.

No module execution, signing, Docker invocation, nonces spent, DB writes, or
automatic editorial/publishing approvals. This is a LOCAL evidence inspection;
the filesystem and event receipts are not independently authenticated.
"""
from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.workflows.preflight import ROOT
from tools import evie_governed_flow as flow
from tools import evie_hooks_container, evie_container_runner
from tools import evie_supervised_distribution as distribution
from tools import evie_supervised_hooks as hooks
from tools.evie_action_lease_contract import load_lease, verify_local_lease
from tools.evie_attest import load_public_key

SCHEMA = "evie.completion-audit/1"
HEX64 = re.compile(r"^[a-f0-9]{64}$")
ENTRYPOINTS = (
    ("tools/evie_supervised_hooks.py", "legacy_host_hooks", "host_subprocess", False, False),
    ("tools/evie_supervised_distribution.py", "legacy_hash_distribution", "host_subprocess", False, False),
    ("tools/evie_approved_distribution.py", "legacy_signed_distribution", "host_subprocess", True, False),
    ("tools/evie_isolated_distribution.py", "signed_docker_distribution", "docker_second_stage", True, True),
    ("tools/evie_governed_flow.py", "preferred_dual_capsule_controller", "docker_both_stages", True, True),
    ("tools/evie_supervised.py", "legacy_fixed_cad_fixture", "host_subprocess", False, False),
)
MAX_JSON = 32_768


def _read_json(path: Path, cap: int = MAX_JSON) -> dict:
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= cap:
        raise ValueError("missing, linked, or oversized review file")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid JSON review file") from exc
    if not isinstance(obj, dict):
        raise ValueError("review file must contain one object")
    return obj


def _read_bytes(path: Path, cap: int = MAX_JSON) -> bytes:
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= cap:
        raise ValueError("missing, linked, or oversized evidence bytes")
    return path.read_bytes()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _assert(condition: bool, detail: str) -> None:
    if not condition:
        raise ValueError(detail)


def source_exposure() -> dict:
    """Bounded explicit inventory, NOT a comprehensive static security scan."""
    lanes = []
    for relative, name, boundary, signed, docker in ENTRYPOINTS:
        path = ROOT / relative
        _assert(path.is_file() and not path.is_symlink() and path.stat().st_size <= 40_000,
                "expected execution entrypoint missing")
        source = path.read_bytes()
        ast.parse(source, filename=relative)
        lanes.append({
            "entrypoint": relative, "id": name,
            "sourceSha256": _sha(source), "executionBoundary": boundary,
            "signedLeaseRequiredByThisCommand": signed,
            "dockerRequiredByThisCommand": docker,
            "hostExecutionPossible": boundary == "host_subprocess",
            "crossEntrypointEnforcement": False,
            "note": "Source-level declared lane; not a comprehensive call-graph or runtime security proof.",
        })
    return {
        "schemaVersion": SCHEMA,
        "report": "known_entrypoint_inventory",
        "inventoryScope": "six explicitly audited public CLI entrypoints",
        "knownLegacyHostPaths": [x["id"] for x in lanes if x["hostExecutionPossible"]],
        "allRepositoryPathsEnforced": False,
        "unrestrictedExecutionProvenAbsent": False,
        "sourceFiles": lanes,
        "hostRuntimeProbed": False,
        "writesPerformed": False,
        "publishingAuthorized": False,
    }


def _validate_first(folder: Path, first: dict) -> tuple[dict, list[str], str]:
    _assert(first.get("stageOneOSIsolated") is True
            and first.get("stageOneIsolation", {}).get("profile") == evie_hooks_container.PROFILE
            and first["stageOneIsolation"].get("networkMode") == "none",
            "first-stage event lacks isolated profile")
    receipt = _read_json(folder / "hooks" / "review-receipt.json")
    raw = _read_bytes(folder / "hooks" / "nine-hooks.json")
    obj = json.loads(raw)
    sha = _sha(raw)
    _assert(receipt.get("schemaVersion") == hooks.SCHEMA
            and receipt.get("status") == "staged_for_human_review"
            and receipt.get("topic") == first["topic"]
            and receipt.get("workflowSourceSha256") == first["workflowSourceSha256"]
            and receipt.get("artifactSha256") == first["hooksArtifactSha256"] == sha
            and receipt.get("artifactBytes") == len(raw)
            and receipt.get("hookCount") == 9
            and receipt.get("categoryCount") == 3
            and receipt.get("executionIsolation") == first["stageOneIsolation"],
            "first-stage digest, source, or declared profile mismatch")
    gov = receipt.get("governance", {})
    _assert(isinstance(gov, dict)
            and gov.get("localModuleExecuted") is True
            and gov.get("externalPublishing") is False
            and gov.get("signed") is False
            and gov.get("authorizedForFutureRuns") is False,
            "first-stage governance overstated")
    lines = obj.get("hooks")
    _assert(obj.get("topic") == first["topic"]
            and isinstance(lines, list) and len(lines) == 9
            and all(isinstance(line, str) and 3 <= len(line) <= 1000 for line in lines)
            and obj.get("categories") == {
                "educational": lines[:3],
                "controversial": lines[3:6],
                "curiosity": lines[6:9],
            }, "first-stage output content invalid")
    source_hashes = hooks.source_check()[2]
    _assert(all(receipt.get(field) == source_hashes[name] for name, field in (
        (hooks.SOURCES[0], "moduleSourceSha256"),
        (hooks.SOURCES[1], "wrapperSourceSha256"),
        (hooks.SOURCES[2], "workerSourceSha256"),
    )), "first-stage producer code digest mismatch")
    return receipt, lines, sha


def _validate_second(folder: Path, first: dict, attempt: dict, finished: dict,
                     first_lines: list[str], first_sha: str) -> tuple[dict, dict]:
    _assert(finished.get("finalDone") is False
            and finished.get("externalPublishingAuthorized") is False
            and finished.get("editorialApprovalGranted") is False
            and finished.get("signedLeaseVerifiedByRunner") is True
            and finished.get("dockerProfile") == evie_container_runner.PROFILE,
            "second-stage event inflates authority")
    second = folder / "distribution"
    blob = _read_bytes(second / "distribution-draft.json")
    draft = json.loads(blob)
    receipt = _read_json(second / "distribution-review-receipt.json")
    consumption = _read_json(second / "lease-consumption.json")
    second_sha = _sha(blob)
    _assert(receipt.get("schemaVersion") == distribution.SCHEMA
            and receipt.get("status") == "staged_for_human_review"
            and receipt.get("approvedInputSha256") == first_sha
            and receipt.get("distributionSha256") == finished.get("distributionSha256") == second_sha
            and receipt.get("distributionBytes") == len(blob)
            and receipt.get("workflowSourceSha256") == first["workflowSourceSha256"]
            and receipt.get("hooksConsumed") == 5,
            "downstream receipt not bound to exact input/output bytes")
    hashes = distribution._source_check()[2]
    _assert(all(receipt.get(field) == hashes[path] for path, field in (
        (distribution.FILES[0], "distributionSourceSha256"),
        (distribution.FILES[1], "distributionWrapperSha256"),
        (distribution.FILES[2], "workerSourceSha256"),
    )), "downstream producer code differs from receipt")
    gov = receipt.get("governance", {})
    _assert(isinstance(gov, dict)
            and gov.get("localSecondModuleExecuted") is True
            and gov.get("externalPublishing") is False
            and gov.get("editorialApprovalGranted") is False
            and gov.get("furtherExecutionAuthorized") is False,
            "downstream receipt claims forbidden effects")
    _assert(isinstance(draft, dict) and draft.get("topic") == first["topic"]
            and draft.get("hooks_used") == first_lines[:5]
            and draft.get("tiktok_hooks") == first_lines[:5]
            and isinstance(draft.get("twitter_thread"), list),
            "actual downstream draft differs from approved first five hooks")
    _assert(consumption.get("schemaVersion") == "evie.local-lease-consumption/1"
            and consumption.get("nonce") == attempt.get("leaseNonce")
            and consumption.get("artifactSha256") == first_sha
            and consumption.get("distributionSha256") == second_sha
            and consumption.get("approvalSignatureVerified") is True
            and consumption.get("localNonceConsumed") is True
            and consumption.get("containerIsolation", {}).get("profile") == evie_container_runner.PROFILE
            and consumption.get("containerIsolation", {}).get("networkMode") == "none"
            and consumption.get("signedExecutionReceipt") is False
            and consumption.get("publishingAuthorized") is False
            and consumption.get("recipientAccepted") is False,
            "second-stage lease consumption observation invalid")
    return receipt, consumption


def _verify_approval(folder: Path, first: dict, attempt: dict, consumption: dict,
                     lease_path: str, public_path: str, ledger_path: str) -> dict:
    # A historical lease must be valid AT THE RECORDED ATTEMPT, not still unexpired now.
    # The attemptedAt field is an unsigned local timestamp, NOT trusted time evidence.
    recorded = attempt.get("attemptedAt")
    _assert(isinstance(recorded, str) and recorded.endswith("Z"),
            "invalid recorded attempt timestamp")
    try:
        checked_at = datetime.fromisoformat(recorded.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("malformed attempt timestamp") from exc
    _assert(checked_at.tzinfo is not None, "attempt timestamp is not UTC")
    lease = load_lease(lease_path)
    key = load_public_key(public_path)
    body = verify_local_lease(
        lease, key,
        artifact_sha=first["hooksArtifactSha256"],
        source_sha=first["workflowSourceSha256"],
        stage_dir=str(folder / "distribution"), now=checked_at,
        historical_completed=True,
    )
    _assert(attempt.get("leaseNonce") == body["nonce"]
            and consumption.get("nonce") == body["nonce"]
            and attempt.get("requestedTimeoutSeconds", 999) <= body["limits"]["maxWallSeconds"],
            "signed lease nonce or runtime limits do not match stage 2")
    ledger = Path(ledger_path).expanduser().absolute()
    _assert(ledger.is_file() and not ledger.is_symlink() and ledger.stat().st_size <= 2_000_000,
            "local spent nonce ledger unavailable")
    # A READ-ONLY SQLite connection; nonexistent paths must never create a file.
    uri = ledger.as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True, timeout=2) as db:
        db.execute("PRAGMA query_only=ON")
        rows = db.execute(
            "SELECT artifact FROM spent_local_leases WHERE nonce=?",
            (body["nonce"],),
        ).fetchall()
    _assert(rows == [(first["hooksArtifactSha256"],)],
            "nonce not verifiably spent in selected local ledger")
    return {
        "historicalLeaseSignatureValid": True,
        "leaseMatchedSourceArtifactDestination": True,
        "recordedAttemptWithinSignedWindow": True,
        "singleHostLedgerNonceFound": True,
        "realWorldOperatorIdentityAuthenticated": False,
        "historicalTimestampIndependentlyTrusted": False,
        "note": "Valid signature and matching local ledger entry, not independent host or time attestation.",
    }


def audit_session(session_dir: str, *, lease_file: str | None = None,
                  trusted_public: str | None = None,
                  ledger: str | None = None) -> dict:
    """Inspect all evidence in read-only mode; no success without exact checks."""
    arguments = (lease_file, trusted_public, ledger)
    if any(x is not None for x in arguments) and not all(arguments):
        raise ValueError("lease file, trusted public key, and ledger must be supplied together")
    folder, first, _ = flow._read_session(session_dir)
    status = flow.session_status(session_dir)
    _, lines, digest = _validate_first(folder, first)
    state = status["state"]
    verified = ["current_source", "stage1_exact_artifact", "stage1_local_docker_profile_declared"]
    approval = {
        "historicalLeaseSignatureValid": False,
        "singleHostLedgerNonceFound": False,
        "realWorldOperatorIdentityAuthenticated": False,
        "historicalTimestampIndependentlyTrusted": False,
    }
    contract = "WAITING_FOR_REVIEW"
    if state == flow.STATES[1]:
        contract = "ATTEMPT_OUTCOME_UNKNOWN"
        verified.append("non_replayable_session_attempt_marker")
    elif state == flow.STATES[2]:
        attempt = flow._json_file(folder / flow.EVENT_2)
        finished = flow._json_file(folder / flow.EVENT_3)
        _, consumption = _validate_second(folder, first, attempt, finished, lines, digest)
        verified.extend(["stage2_exact_artifact", "five_hook_handoff", "stage2_local_docker_profile_declared"])
        if all(arguments):
            approval = _verify_approval(folder, first, attempt, consumption,
                                        lease_file, trusted_public, ledger)
            verified.extend(["independent_public_key_signature_check",
                             "historical_scope_check", "local_nonce_spend_check"])
            contract = "LOCAL_DRAFT_CONTRACT_VERIFIED"
        else:
            contract = "DRAFT_STAGED_APPROVAL_UNVERIFIED"
    return {
        "schemaVersion": SCHEMA,
        "report": "session_completion_evidence",
        "workflow": flow.FLOW,
        "sessionState": state,
        "completionContract": {
            "scope": "local_two_stage_draft_handoff_only",
            "status": contract,
            "evidenceChecksPassed": verified,
            "fullyVerified": contract == "LOCAL_DRAFT_CONTRACT_VERIFIED",
            "source": "local-files-and-one-intact-sqlite-ledger",
        },
        "authorization": approval,
        "policy": {
            "publishingAuthorized": False,
            "editorialAcceptanceVerified": False,
            "externallyAuthenticatedExecution": False,
            "finalProductDone": False,
            "automaticRetryAllowed": False,
            "noRuntimeExecutedByAuditor": True,
            "noFilesWrittenByAuditor": True,
        },
        "observationsAreUnsigned": True,
        "note": ("Completion means only that a local content DRAFT satisfies this narrow "
                 "contract. No authenticated recipient, publishing, independently "
                 "trusted Docker telemetry, or final release DONE is proven."),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="EVIE R20 read-only evidence audit; no execution and no writes")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("entrypoints")
    audit = sub.add_parser("session")
    audit.add_argument("--session-dir", required=True)
    audit.add_argument("--lease-file")
    audit.add_argument("--trusted-public")
    audit.add_argument("--ledger")
    args = parser.parse_args()
    try:
        result = source_exposure() if args.command == "entrypoints" else audit_session(
            args.session_dir, lease_file=args.lease_file,
            trusted_public=args.trusted_public, ledger=args.ledger,
        )
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, sqlite3.Error, KeyError, TypeError,
            UnicodeError, json.JSONDecodeError):
        print(json.dumps({
            "schemaVersion": SCHEMA, "report": "rejected",
            "completionContract": {"status": "EVIDENCE_REJECTED", "fullyVerified": False},
            "finalProductDone": False, "publishingAuthorized": False,
            "reason": "source-or-local-evidence-invalid",
        }))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
