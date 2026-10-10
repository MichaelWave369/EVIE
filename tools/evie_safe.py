"""R21 default EVIE local CLI: an ALLOWLISTED front door, not an OS policy.

Only these five source-bounded operations exist: plan, start, status, resume,
audit; plus policy and entrypoints read-only visibility. No dynamic module
dispatch, generic subprocess, publication, automatic signer, credentials,
scheduler, or host-Python fallback through the governed path.

Legacy R13-R17 CLIs remain separately callable. This module CANNOT revoke a
person's host-level permission to run them or other repository Python files.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from argparse import Namespace
from typing import Any

from tools import evie_completion_audit as audit
from tools import evie_governed_flow as governed

SCHEMA = "evie.safe-entry/1"
DEFAULT_WORKFLOW = "local_hooks_to_distribution_review"
COMMANDS = frozenset(("policy", "entrypoints", "plan", "start", "status", "resume", "audit"))
LEGACY_ENTRYPOINT_IDS = frozenset((
    "legacy_host_hooks", "legacy_hash_distribution",
    "legacy_signed_distribution", "legacy_fixed_cad_fixture",
))
# Strictly authored references, not import targets or parameters to dispatch.
RECOMMENDED = "python -m tools.evie_safe"
LEGACY_STATUS = "legacy_compatibility_only_not_restricted_by_this_cli"


def _ensure_approval_triplet(lease_file: str | None,
                             trusted_public: str | None,
                             ledger: str | None) -> None:
    pieces = (lease_file, trusted_public, ledger)
    if any(x is not None for x in pieces) and not all(
            isinstance(x, str) and x.strip() for x in pieces):
        raise ValueError("audit needs all three independent approval evidence paths")


def policy_report() -> dict[str, Any]:
    """Read source inventory without running a worker or changing host state."""
    inventory = audit.source_exposure()
    rows = []
    for entry in inventory["sourceFiles"]:
        legacy = entry["id"] in LEGACY_ENTRYPOINT_IDS
        rows.append({
            "id": entry["id"],
            "entrypoint": entry["entrypoint"],
            "sourceSha256": entry["sourceSha256"],
            "migrationDisposition": LEGACY_STATUS if legacy
                                    else "direct_advanced_opt_in",
            "hostExecutionPossible": entry["hostExecutionPossible"],
            "signedLeaseRequiredByThisCommand": entry["signedLeaseRequiredByThisCommand"],
            "dockerRequiredByThisCommand": entry["dockerRequiredByThisCommand"],
            "blockedBySafeEntryIfInvokedAsAction": True,
        })
    return {
        "schemaVersion": SCHEMA,
        "report": "declared_local_default_route",
        "recommendedCommand": RECOMMENDED,
        "workflow": DEFAULT_WORKFLOW,
        "allowedActions": ["policy", "entrypoints", "plan", "start", "status", "resume", "audit"],
        "start": {
            "requiresExplicitOperatorConfirmation": True,
            "isolatedHooksDocker": True,
            "autoResumes": False,
            "createsSignedApprovals": False,
        },
        "resume": {
            "requiresExplicitOperatorConfirmation": True,
            "requiresIndependentSignedLease": True,
            "requiresOfflineDocker": True,
            "requiresIntactLocalNonceLedger": True,
            "autoRetry": False,
        },
        "legacyRoutes": rows,
        "legacyCommandsRemoved": False,
        "repositoryWideHostExecutionPrevented": False,
        "networkOrHostIsolationProvenByThisReport": False,
        "publishingAuthorized": False,
        "finalDoneAuthorized": False,
        "noWorkerExecuted": True,
        "noFilesWritten": True,
        "note": ("The default front door refuses unsupported actions. "
                 "Direct compatibility CLIs still exist outside this boundary."),
    }


def dispatch(args: Namespace) -> dict[str, Any]:
    """Explicit fixed call sites only, never caller-provided module names."""
    command = getattr(args, "command", None)
    if command not in COMMANDS:
        raise ValueError("action not allowlisted by EVIE safe entry")
    if command == "policy":
        return policy_report()
    if command == "entrypoints":
        result = audit.source_exposure()
        return {
            "schemaVersion": SCHEMA, "mode": "read_only_known_entrypoints",
            "data": result, "publishingAuthorized": False,
        }
    if command == "plan":
        return {
            "schemaVersion": SCHEMA, "mode": "source_only_governed_plan",
            "data": governed.plan(), "publishingAuthorized": False,
        }
    if command == "start":
        if args.confirm_local_execution is not True:
            raise ValueError("starting isolated hooks requires explicit confirmation")
        result = governed.start_session(
            session_dir=args.session_dir, script_file=args.script_file,
            topic=args.topic, timeout=args.timeout, confirm=True,
        )
        if (result.get("stageOneOSIsolated") is not True
                or result.get("state") != governed.STATES[0]
                or result.get("stageTwoExecuted") is not False):
            raise ValueError("safe entry did not receive the governed paused event")
        return {"schemaVersion": SCHEMA, "mode": "governed_hooks_paused",
                "data": result, "publishingAuthorized": False}
    if command == "status":
        return {
            "schemaVersion": SCHEMA, "mode": "read_only_session_status",
            "data": governed.session_status(args.session_dir),
            "publishingAuthorized": False,
        }
    if command == "resume":
        if args.confirm_local_execution is not True:
            raise ValueError("signed Docker resume requires explicit confirmation")
        result = governed.resume_session(
            session_dir=args.session_dir, lease_file=args.lease_file,
            trusted_public=args.trusted_public, ledger=args.ledger,
            timeout=args.timeout, confirm=True,
        )
        if (result.get("state") != governed.STATES[2]
                or result.get("finalDone") is not False
                or result.get("externalPublishingAuthorized") is not False):
            raise ValueError("unexpected downstream result or approval state")
        return {"schemaVersion": SCHEMA, "mode": "governed_draft_staged",
                "data": result, "publishingAuthorized": False}
    # command == "audit"; an audit NEVER calls governed.resume_session.
    _ensure_approval_triplet(args.lease_file, args.trusted_public, args.ledger)
    return {
        "schemaVersion": SCHEMA, "mode": "read_only_completion_audit",
        "data": audit.audit_session(
            args.session_dir, lease_file=args.lease_file,
            trusted_public=args.trusted_public, ledger=args.ledger,
        ),
        "publishingAuthorized": False,
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Preferred local EVIE entry: audited two-stage draft ONLY. "
                    "Old direct CLIs remain available outside this gate."
    )
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("policy", help="read-only source-bound migration inventory")
    sub.add_parser("entrypoints", help="read-only known local CLI exposure inventory")
    sub.add_parser("plan", help="read-only original two-stage source plan")
    start = sub.add_parser("start", help="explicitly produce isolated hooks and STOP")
    start.add_argument("--session-dir", required=True)
    start.add_argument("--script-file", required=True)
    start.add_argument("--topic", required=True)
    start.add_argument("--timeout", type=int, default=20)
    start.add_argument("--confirm-local-execution", action="store_true")
    status = sub.add_parser("status", help="read-only governed session state")
    status.add_argument("--session-dir", required=True)
    resume = sub.add_parser("resume", help="explicit signed, single-use offline Docker resume")
    resume.add_argument("--session-dir", required=True)
    resume.add_argument("--lease-file", required=True)
    resume.add_argument("--trusted-public", required=True)
    resume.add_argument("--ledger", required=True)
    resume.add_argument("--timeout", type=int, default=20)
    resume.add_argument("--confirm-local-execution", action="store_true")
    check = sub.add_parser("audit", help="read-only narrow completion evidence")
    check.add_argument("--session-dir", required=True)
    check.add_argument("--lease-file")
    check.add_argument("--trusted-public")
    check.add_argument("--ledger")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = dispatch(args)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError,
            sqlite3.Error, UnicodeError, json.JSONDecodeError):
        print(json.dumps({
            "schemaVersion": SCHEMA,
            "status": "rejected",
            "reason": "unsupported-or-unverified-governed-action",
            "legacyFallback": False,
            "publishingAuthorized": False,
            "finalDoneAuthorized": False,
        }))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
