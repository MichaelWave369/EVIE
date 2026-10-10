"""R23: default-deny service execution security contract.

A *read-only* readiness assessment, NOT a mechanism for granting privileges.
The R22 HTTP service still exposes zero execution endpoints, and this module
must never sign, consume a lease, import workers, execute Docker, or write state.

An HTTP bearer token proves possession, NOT a caller's OS identity. A signed
local lease and a SQLite row also do not establish service-wide enforcement.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from app.workflows.preflight import ROOT

SCHEMA = "evie.execution-security-contract/1"
MODE = "READ_ONLY_NO_HTTP_EXECUTION"
EXECUTION_ACTIONS = frozenset({"start", "resume", "publish", "execute", "dispatch"})
CONTRACT_SOURCES = (
    "tools/evie_local_service.py",
    "tools/evie_safe.py",
    "tools/evie_governed_flow.py",
    "tools/evie_action_lease_contract.py",
    "tools/evie_container_runner.py",
    "tools/evie_execution_security.py",
)

# Values represent things **not yet enforced by the R22 service itself**.
# Do not accept caller input to flip these flags or infer them from possession
# of the R22 bearer secret or a user-controlled receipt.
BLOCKERS = (
    ("authenticated_os_client_principal", "No authenticated per-request OS client identity."),
    ("isolated_service_privilege_boundary", "HTTP service is not an OS-separated execution broker."),
    ("protected_approval_and_nonce_store", "Signed approval nonce store remains a replaceable local file."),
    ("mandatory_enforcement_across_legacy_clis", "Legacy host CLIs remain directly invocable."),
    ("single_use_service_side_request_binding", "No service-owned atomic request-to-approval binding."),
    ("independently_attested_runtime_receipt", "Local execution events are not independently attested."),
)
REQUIRED_FOR_PROMOTION = tuple(code for code, _ in BLOCKERS)


def _source_digests() -> dict[str, str]:
    """Bounded source inventory, not runtime process attestation."""
    results = {}
    for name in CONTRACT_SOURCES:
        file = ROOT / name
        if (not file.is_file() or file.is_symlink()
                or not 0 < file.stat().st_size <= 65_536):
            raise ValueError("missing or untrusted execution-contract source file")
        results[name] = hashlib.sha256(file.read_bytes()).hexdigest()
    return results


def assess() -> dict:
    """Pure, deterministic deny decision, even on an otherwise healthy host.

    Readable source and valid existing signatures are insufficient to authorize
    a future HTTP execution API. This module has NO promotion override.
    """
    digests = _source_digests()
    blockers = [
        {"requirement": code, "satisfied": False, "reason": description}
        for code, description in BLOCKERS
    ]
    return {
        "schemaVersion": SCHEMA,
        "contractMode": MODE,
        "status": "EXECUTION_GATE_CLOSED",
        "sourceSha256": digests,
        "boundaries": {
            "httpLoopbackReadOnly": True,
            "httpExecutionRoutesEnabled": False,
            "callerOsIdentityAuthenticated": False,
            "bearerTokenIsOsIdentity": False,
            "directLegacyCliPathsStillExist": True,
            "localSqliteIsTamperProof": False,
            "signedApprovalCanBeIssuedByHttp": False,
            "httpCanConsumeLease": False,
            "automaticSigningAllowed": False,
            "publicPublishingAllowed": False,
        },
        "promotionRequirements": blockers,
        "promotionReady": False,
        "executionAllowed": False,
        "networkOrHostSecurityIndependentlyAttested": False,
        "noWorkerExecuted": True,
        "noFilesWritten": True,
        "note": ("Read-only proposed execution-service security contract. "
                 "Do not mistake working Docker and signed local CLIs for "
                 "authenticated or enforced HTTP execution authority."),
    }


def deny_http_execution(*, intent: object = None) -> dict:
    """Untrusted data cannot authorize transport-mediated execution.

    A caller may supply a forged principal, expiry, lease or proof object.
    None is consulted to grant authority. This function has no side effects.
    """
    return {
        "schemaVersion": SCHEMA,
        "status": "DENIED",
        "reason": "http_execution_service_not_qualified",
        "executionAllowed": False,
        "approvalConsumed": False,
        "workerStarted": False,
        "publishingAuthorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="R23 read-only execution service readiness audit")
    actions = parser.add_subparsers(dest="command", required=True)
    actions.add_parser("assess", help="read-only security blockers and source digest inventory")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(assess(), indent=2))
        return 0
    except (OSError, ValueError, TypeError):
        print(json.dumps({
            "schemaVersion": SCHEMA,
            "status": "EXECUTION_GATE_CLOSED",
            "executionAllowed": False,
            "reason": "security_contract_source_unavailable",
        }))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
