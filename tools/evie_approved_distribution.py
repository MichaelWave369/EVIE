"""R16 preferred signed lane: verify and BURN local lease, then invoke R15 draft.

This does not disable R15's earlier operator-only CLI. Lease enforcement applies
ONLY when this new command is used. It cannot restrict someone with OS access
from directly running the legacy local module.
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from tools import evie_supervised_distribution as dist
from tools.evie_action_lease_contract import (
    consume_local_lease, load_lease, verify_local_lease,
)
from tools.evie_attest import load_public_key, fingerprint
from tools.evie_supervised import _write_new

SCHEMA = "evie.local-lease-consumption/1"


def run_with_local_lease(*, hooks_dir: str, approved_hooks_sha256: str,
                         stage_dir: str, lease_file: str, trusted_public: str,
                         ledger: str, confirm: bool, timeout: int = 20,
                         worker_backend=None, isolation_metadata=None) -> dict:
    if confirm is not True:
        raise ValueError("local execution must be explicitly confirmed")
    if type(timeout) is not int or not 1 <= timeout <= 20:
        raise ValueError("invalid requested execution budget")
    # Validate before burning: only known R15 first-stage artifacts, exact source,
    # no existing output folder, explicit trust anchor and signed scope.
    dest = dist._stage_directory(stage_dir)
    _, source_sha, _ = dist._source_check()
    dist._load_approved_first_stage(hooks_dir, approved_hooks_sha256, source_sha)
    trust = load_public_key(trusted_public)
    body = verify_local_lease(
        load_lease(lease_file), trust,
        artifact_sha=approved_hooks_sha256, source_sha=source_sha,
        stage_dir=str(dest),
    )
    if timeout > body["limits"]["maxWallSeconds"]:
        raise ValueError("requested timeout exceeds signed budget")
    # Irreversible local burn precedes execution: failed attempts cannot replay.
    consume_local_lease(body, ledger)
    result = dist.stage_distribution(
        hooks_dir=hooks_dir, approved_hooks_sha256=approved_hooks_sha256,
        stage_dir=str(dest), confirm=True, timeout=timeout,
        worker_backend=worker_backend,
    )
    observation = {
        "schemaVersion": SCHEMA,
        "origin": "local-unsigned-ledger-observation",
        "status": "second-stage-staged",
        "action": body["action"],
        "nonce": body["nonce"],
        "trustedKeyFingerprint": fingerprint(trust),
        "approvalSignatureVerified": True,
        "localNonceConsumed": True,
        "artifactSha256": approved_hooks_sha256,
        "distributionSha256": result["distributionSha256"],
        "executedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "ledgerScope": "one-local-file-on-one-host",
        "containerIsolation": isolation_metadata or {
            "profile": "legacy-local-subprocess", "externalNetworkRestricted": False,
        },
        "signedExecutionReceipt": False,
        "externallyAuthenticatedExecution": False,
        "publishingAuthorized": False,
        "recipientAccepted": False,
    }
    _write_new(dest / "lease-consumption.json", (json.dumps(observation, indent=2) + "\n").encode())
    return observation


def main() -> int:
    p = argparse.ArgumentParser(description="R16 one-use signed lease for local distribution draft ONLY")
    p.add_argument("--hooks-dir", required=True)
    p.add_argument("--approved-hooks-sha256", required=True)
    p.add_argument("--stage-dir", required=True)
    p.add_argument("--lease-file", required=True)
    p.add_argument("--trusted-public", required=True)
    p.add_argument("--ledger", required=True, help="persistent local SQLite nonce ledger OUTSIDE repo")
    p.add_argument("--confirm-local-execution", action="store_true")
    p.add_argument("--timeout", type=int, default=20)
    args = p.parse_args()
    try:
        observation = run_with_local_lease(
            hooks_dir=args.hooks_dir, approved_hooks_sha256=args.approved_hooks_sha256,
            stage_dir=args.stage_dir, lease_file=args.lease_file,
            trusted_public=args.trusted_public, ledger=args.ledger,
            confirm=args.confirm_local_execution, timeout=args.timeout,
        )
        print(json.dumps(observation, indent=2))
        return 0
    except (ValueError, TypeError, OSError, UnicodeError, json.JSONDecodeError):
        print(json.dumps({"schemaVersion": SCHEMA, "status": "rejected",
                          "reason": "invalid-spent-or-expired-lease-or-execution-failed",
                          "publishingAuthorized": False, "recipientAccepted": False}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
