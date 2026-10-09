"""Explicit local qualification lab. Does not qualify arbitrary EVIE modules."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT_SCHEMA = "evie.qualification-receipt/1"
SCENARIOS = {
    "openblueprint_floor_plan": {
        "id": "cad_rectangular_concept_v1",
        "source": "app/modules/openblueprint_floor_plan.py",
        "worker": "tools.evie_qualify_worker",
        "effects": "temporary-files-only",
    },
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_CHECKS = frozenset({
    "versioned_proposal", "versioned_project", "bounded_wall_geometry",
    "symbol_types", "unique_element_ids", "source_labels", "run_id_bound",
    "digest_match", "artifact_scope",
})
# Keep this explicit. Running in a child process with -I is not OS sandboxing.
SAFE_ENV_KEYS = ("PATH", "SystemRoot", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME",
                 "USERPROFILE", "LOCALAPPDATA", "APPDATA", "LANG", "LC_ALL", "VIRTUAL_ENV")

def available_scenarios() -> list[dict]:
    return [{"module": module, "scenario": s["id"], "allowedEffects": s["effects"]}
            for module, s in SCENARIOS.items()]

def _checked_observation(raw: object, module: str, expected_source: str) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("malformed worker observation")
    if (raw.get("schemaVersion") != "evie.qualification-observation/1"
        or raw.get("module") != module or raw.get("scenario") != SCENARIOS[module]["id"]
        or raw.get("status") != "pass"):
        raise ValueError("worker did not confirm expected scenario")
    checks = raw.get("checks")
    if not isinstance(checks, dict) or set(checks) != EXPECTED_CHECKS or any(v is not True for v in checks.values()):
        raise ValueError("incomplete or failed worker checks")
    for key in ("sourceSha256", "artifactSha256"):
        if not isinstance(raw.get(key), str) or HEX64.fullmatch(raw[key]) is None:
            raise ValueError("invalid worker digest")
    if raw["sourceSha256"] != expected_source:
        raise ValueError("worker source digest differs from local code")
    if raw.get("observedWalls") != 5 or raw.get("observedSymbols") != 2:
        raise ValueError("unexpected output shape")
    return {"checks": checks, "sourceSha256": raw["sourceSha256"],
            "artifactSha256": raw["artifactSha256"], "observedWalls": 5, "observedSymbols": 2}

def run_qualification(module: str, timeout: int = 15) -> dict:
    """Explicitly run one fixed, offline-oriented, audited fixture; never accept arbitrary code."""
    if module not in SCENARIOS:
        raise ValueError("Module is not allowlisted for qualification")
    if type(timeout) is not int or not 1 <= timeout <= 30:
        raise ValueError("Timeout must be between 1 and 30 seconds")
    entry = SCENARIOS[module]
    source = ROOT / entry["source"]
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    receipt = {
        "schemaVersion": RECEIPT_SCHEMA,
        "module": module,
        "scenario": entry["id"],
        "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "origin": "local-subprocess-observation",
        "status": "fail",
        "checks": {},
        "sourceSha256": source_sha,
        "artifactSha256": None,
        "durationMs": 0,
        "effectPolicy": {"allowlisted": True, "temporaryWorkspace": True,
                         "providerEnvironmentStripped": True,
                         "networkSandboxEnforced": False,
                         "externalEffectsAuthorized": False},
        "trust": {"signed": False, "authenticatedMachine": False,
                  "scope": "fixed deterministic fixture only",
                  "note": "Local self-reported test observation, not a trusted signature or production readiness."},
    }
    env = {k: os.environ[k] for k in SAFE_ENV_KEYS if k in os.environ}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    command = [sys.executable, "-I", "-c",
               "import sys;sys.path.insert(0,sys.argv[1]);"
               "from tools.evie_qualify_worker import main;raise SystemExit(main())",
               str(ROOT)]
    started = time.monotonic()
    try:
        with tempfile.TemporaryDirectory(prefix="evie-qualification-") as tmp:
            result = subprocess.run(command, cwd=tmp, env=env,
                                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                    timeout=timeout, check=False)
        if len(result.stdout) > 32_768:
            raise ValueError("worker output exceeded 32 KB")
        if result.returncode != 0:
            raise ValueError("worker failed")
        observation = _checked_observation(json.loads(result.stdout.decode("utf-8")), module, source_sha)
        receipt.update(observation)
        receipt["status"] = "pass"
    except subprocess.TimeoutExpired:
        receipt["reason"] = "timeout"
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, KeyError):
        receipt["reason"] = "qualification-failed"
    finally:
        receipt["durationMs"] = max(0, round((time.monotonic() - started) * 1000))
    return receipt

def write_receipt_exclusive(path: str, receipt: dict) -> None:
    """Write only on explicit request; never overwrite or follow a receipt-file symlink."""
    location = Path(path).expanduser()
    if not location.parent.is_dir():
        raise ValueError("Receipt parent directory does not exist")
    data = (json.dumps(receipt, indent=2) + "\n").encode("utf-8")
    if len(data) > 64_000:
        raise ValueError("Receipt too large")
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(location, flags, 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(data)

def main() -> int:
    parser = argparse.ArgumentParser(description="EVIE qualification: explicitly allowlisted, disposable local smoke only.")
    command = parser.add_subparsers(dest="command", required=True)
    command.add_parser("list", help="list fixed, allowlisted scenarios")
    run = command.add_parser("run", help="qualify one allowlisted fixed scenario")
    run.add_argument("module", choices=sorted(SCENARIOS))
    run.add_argument("--receipt", help="optionally write JSON receipt to new, existing-parent destination")
    run.add_argument("--timeout", type=int, default=15)
    run.add_argument("--signing-key", help="encrypted Ed25519 private key, used only after a successful local run")
    run.add_argument("--attestation", help="write new signed attestation JSON using --signing-key")
    args = parser.parse_args()
    if args.command == "list":
        print(json.dumps({"schemaVersion": "evie.qualification-scenarios/1",
                          "scenarios": available_scenarios()}, indent=2))
        return 0
    try:
        receipt = run_qualification(args.module, timeout=args.timeout)
        if bool(args.signing_key) != bool(args.attestation):
            raise ValueError("signing needs both --signing-key and --attestation")
        if args.receipt and args.attestation and Path(args.receipt).resolve() == Path(args.attestation).resolve():
            raise ValueError("receipt and attestation paths must be different")
        if args.attestation:
            if receipt["status"] != "pass":
                raise ValueError("refuse to sign a failed qualification")
            from tools.evie_attest import load_private_key, sign_local_receipt, _exclusive_write
            import getpass
            private = load_private_key(args.signing_key, getpass.getpass("Private-key passphrase: "))
            attestation = sign_local_receipt(receipt, private)
            _exclusive_write(args.attestation, (json.dumps(attestation, indent=2) + "\n").encode("utf-8"))
        if args.receipt:
            write_receipt_exclusive(args.receipt, receipt)
        print(json.dumps(receipt, indent=2))
        return 0 if receipt["status"] == "pass" else 1
    except (ValueError, OSError):
        print(json.dumps({"status": "fail", "reason": "invalid-arguments-or-receipt-path"}))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
