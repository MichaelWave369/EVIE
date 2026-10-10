"""R16 operator CLI: issue / verify Ed25519 one-use local distribution leases.

Signing is an explicit local operator gesture with an encrypted private key;
verification uses a separately selected trusted public key. No execution here.
"""
from __future__ import annotations
import argparse
import getpass
import json

from tools.evie_attest import _exclusive_write, load_private_key, load_public_key
from tools import evie_supervised_distribution as dist
from tools.evie_action_lease_contract import (
    issue_local_lease, verify_local_lease, load_lease,
)

def approved_context(hooks_dir: str, digest: str) -> str:
    _, source_sha, _ = dist._source_check()
    dist._load_approved_first_stage(hooks_dir, digest, source_sha)
    return source_sha

def main() -> int:
    parser = argparse.ArgumentParser(description="R16 local signed lease, never a publishing permission")
    actions = parser.add_subparsers(dest="action", required=True)
    issue = actions.add_parser("issue")
    verify = actions.add_parser("verify")
    for p in (issue, verify):
        p.add_argument("--hooks-dir", required=True)
        p.add_argument("--approved-hooks-sha256", required=True)
        p.add_argument("--stage-dir", required=True, help="new second-stage review folder")
    issue.add_argument("--signing-key", required=True, help="locally encrypted Ed25519 private key")
    issue.add_argument("--lease-file", required=True, help="new output filename, no overwrite")
    issue.add_argument("--ttl-minutes", type=int, default=5)
    issue.add_argument("--max-seconds", type=int, default=20)
    verify.add_argument("--lease-file", required=True)
    verify.add_argument("--trusted-public", required=True)
    args = parser.parse_args()
    try:
        source_sha = approved_context(args.hooks_dir, args.approved_hooks_sha256)
        if args.action == "issue":
            key = load_private_key(args.signing_key, getpass.getpass("Lease-signing key passphrase: "))
            record = issue_local_lease(
                artifact_sha=args.approved_hooks_sha256, source_sha=source_sha,
                stage_dir=args.stage_dir, private_key=key,
                ttl_minutes=args.ttl_minutes, max_seconds=args.max_seconds,
            )
            _exclusive_write(args.lease_file, (json.dumps(record, indent=2) + "\n").encode())
            print(json.dumps({"status": "signed-local-lease-created",
                              "leaseFileCreated": True, "noExecution": True,
                              "keyFingerprint": record["keyFingerprint"]}))
        else:
            lease = load_lease(args.lease_file)
            body = verify_local_lease(
                lease, load_public_key(args.trusted_public),
                artifact_sha=args.approved_hooks_sha256, source_sha=source_sha,
                stage_dir=args.stage_dir,
            )
            print(json.dumps({
                "status": "valid-not-consumed", "action": body["action"],
                "nonce": body["nonce"], "expiresAt": body["expiresAt"],
                "sourceMatched": True, "executionOccurred": False,
                "replayStatusChecked": False,
                "note": "Verification does not check the local ledger or spend a lease.",
            }))
        return 0
    except (ValueError, TypeError, OSError, UnicodeError, json.JSONDecodeError):
        print(json.dumps({"status": "rejected", "actionAuthorized": False,
                          "reason": "signed-local-lease-validation-failed"}))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
