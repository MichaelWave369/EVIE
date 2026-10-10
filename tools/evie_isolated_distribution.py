"""R17: execute exactly one R16 signed distribution lease inside Docker.

No implicit local Python fallback. Does not make the old R15 or R16
execution commands disappear, and does not promise general-purpose orchestration.
"""
from __future__ import annotations

import argparse
import json

from tools.evie_approved_distribution import run_with_local_lease, SCHEMA
from tools.evie_container_runner import image_preflight, isolation_metadata, run_isolated


def run_isolated_with_lease(*, hooks_dir: str, approved_hooks_sha256: str,
                            stage_dir: str, lease_file: str, trusted_public: str,
                            ledger: str, confirm: bool, timeout: int = 20) -> dict:
    if confirm is not True:
        raise ValueError("explicit isolated local execution confirmation required")
    if type(timeout) is not int or not 1 <= timeout <= 20:
        raise ValueError("invalid isolated time budget")
    # Fail closed BEFORE consuming the one-time lease when Docker is missing.
    image_id = image_preflight()
    def secure_worker(topic: str, hooks: list[str], seconds: int) -> dict:
        return run_isolated(topic, hooks, seconds, image_id=image_id)
    return run_with_local_lease(
        hooks_dir=hooks_dir, approved_hooks_sha256=approved_hooks_sha256,
        stage_dir=stage_dir, lease_file=lease_file,
        trusted_public=trusted_public, ledger=ledger, confirm=True,
        timeout=timeout, worker_backend=secure_worker,
        isolation_metadata=isolation_metadata(image_id),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="EVIE R17 signed offline Docker capsule; no fallback")
    parser.add_argument("--hooks-dir", required=True)
    parser.add_argument("--approved-hooks-sha256", required=True)
    parser.add_argument("--stage-dir", required=True)
    parser.add_argument("--lease-file", required=True)
    parser.add_argument("--trusted-public", required=True)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--confirm-local-execution", action="store_true")
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()
    try:
        observation = run_isolated_with_lease(
            hooks_dir=args.hooks_dir, approved_hooks_sha256=args.approved_hooks_sha256,
            stage_dir=args.stage_dir, lease_file=args.lease_file,
            trusted_public=args.trusted_public, ledger=args.ledger,
            confirm=args.confirm_local_execution, timeout=args.timeout,
        )
        print(json.dumps(observation, indent=2))
        return 0
    except (ValueError, TypeError, OSError, UnicodeError, json.JSONDecodeError):
        print(json.dumps({
            "schemaVersion": SCHEMA,
            "status": "rejected",
            "reason": "docker-isolation-or-signed-lease-denied",
            "fallbackToHostPython": False,
            "publishingAuthorized": False,
        }))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
