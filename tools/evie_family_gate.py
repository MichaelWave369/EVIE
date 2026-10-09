"""R8B local family handoff review: prepare, acknowledge, verify. No transfer."""
from __future__ import annotations

import argparse
import getpass
import json
from pathlib import Path

from app.family_gate.contracts import (
    acknowledge, catalog, create_proposal, hash_local_artifact,
    validate_proposal, verify_acknowledgement,
)
from app.family_gate.openblue_preflight import preflight_files
from tools.evie_attest import (
    _exclusive_write, load_private_key, load_public_key,
)

def read_json_file(path: str, limit: int = 32_000) -> dict:
    f = Path(path).expanduser()
    if not f.is_file() or f.stat().st_size > limit:
        raise ValueError("invalid or oversized JSON file")
    value = json.loads(f.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("expected JSON object")
    return value

def save_new(path: str, data: dict) -> None:
    payload = (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    if len(payload) > 48_000:
        raise ValueError("JSON would exceed 48 KB")
    _exclusive_write(path, payload)

def main() -> int:
    parser = argparse.ArgumentParser(
        description="EVIE local family artifact REVIEW only. Does not connect apps or grant job execution."
    )
    sub = parser.add_subparsers(dest="operation", required=True)
    sub.add_parser("catalog", help="display proposed recipient/artifact contracts; transports disabled")
    prepare = sub.add_parser("prepare", help="hash selected local file and write a new read-only proposal")
    prepare.add_argument("--target", required=True, choices=sorted(catalog_target_ids()))
    prepare.add_argument("--kind", required=True)
    prepare.add_argument("--artifact", required=True)
    prepare.add_argument("--proposal", required=True)
    prepare.add_argument("--ttl-minutes", type=int, default=15)
    review = sub.add_parser("acknowledge", help="sign manual-review acknowledgement (NOT an action grant)")
    review.add_argument("--proposal", required=True)
    review.add_argument("--signing-key", required=True)
    review.add_argument("--ack", required=True)
    check = sub.add_parser("verify", help="verify local acknowledgement using a separately pinned public key")
    check.add_argument("--ack", required=True)
    check.add_argument("--trusted-public", required=True)
    inspect = sub.add_parser("inspect-openblue", help="read-only digest+geometry preflight; never import into OpenBlue")
    inspect.add_argument("--proposal", required=True, help="family review JSON envelope")
    inspect.add_argument("--artifact", required=True, help="OpenBlue EVIE proposal JSON file")
    args = parser.parse_args()
    try:
        if args.operation == "catalog":
            print(json.dumps(catalog(), indent=2))
        elif args.operation == "prepare":
            sha, size = hash_local_artifact(args.artifact)
            proposal = create_proposal(args.kind, args.target, sha, size, ttl_minutes=args.ttl_minutes)
            save_new(args.proposal, proposal)
            print(json.dumps({"status": "prepared", "target": proposal["target"],
                              "sha256": sha, "effectsAuthorized": False}, indent=2))
        elif args.operation == "acknowledge":
            proposal = validate_proposal(read_json_file(args.proposal))
            key = load_private_key(args.signing_key, getpass.getpass("Private-key passphrase: "))
            receipt = acknowledge(proposal, key)
            save_new(args.ack, receipt)
            print(json.dumps({"status": "acknowledged", "signed": True,
                              "executionAuthorized": False, "transportEnabled": False}))
        elif args.operation == "verify":
            report = verify_acknowledgement(read_json_file(args.ack, limit=48_000),
                                            load_public_key(args.trusted_public))
            print(json.dumps(report, indent=2))
        else:
            report = preflight_files(args.proposal, args.artifact)
            print(json.dumps(report, indent=2))
        return 0
    except (ValueError, TypeError, OSError, json.JSONDecodeError, UnicodeError):
        print(json.dumps({"status": "fail", "reason": "invalid-input-or-review-key"}))
        return 1

def catalog_target_ids() -> list[str]:
    return [entry["id"] for entry in catalog()["targets"]]

if __name__ == "__main__":
    raise SystemExit(main())
