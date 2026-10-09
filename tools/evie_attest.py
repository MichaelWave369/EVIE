"""EVIE R8: opt-in Ed25519 local attestation; never an execution grant.

Trust root: an independently selected public key file. Self-declared key IDs
inside a receipt are NOT trust anchors. Private keys never enter subprocesses.
"""
from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

SCHEMA = "evie.qualification-attestation/1"
DOMAIN = b"EVIE/QUALIFICATION_ATTESTATION_V1\x00"
MAX_ATTESTATION_BYTES = 128_000
HEX64 = re.compile(r"^[0-9a-f]{64}$")

def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")

def strict_decode(value: str, *, cap: int) -> bytes:
    if not isinstance(value, str) or len(value) > (cap * 4 // 3 + 8):
        raise ValueError("invalid or oversized base64")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, base64.binascii.Error):
        raise ValueError("malformed base64") from None
    if len(decoded) > cap:
        raise ValueError("decoded payload exceeds limit")
    return decoded

def spki_bytes(public: Ed25519PublicKey) -> bytes:
    return public.public_bytes(
        encoding=serialization.Encoding.DER, format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

def fingerprint(public: Ed25519PublicKey) -> str:
    return hashlib.sha256(spki_bytes(public)).hexdigest()

def _exclusive_write(path: str | Path, payload: bytes, *, permission: int = 0o600) -> None:
    dest = Path(path).expanduser()
    if not dest.parent.is_dir():
        raise ValueError("destination directory must already exist")
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(dest, flags, permission)
    try:
        with os.fdopen(fd, "wb") as target:
            target.write(payload)
    except BaseException:
        dest.unlink(missing_ok=True)
        raise

def create_keypair(private_path: str, public_path: str, password: str) -> str:
    """Both paths must be new. Private key is encrypted with an operator passphrase."""
    if len(password) < 12:
        raise ValueError("private-key passphrase must contain at least 12 characters")
    private, public = Path(private_path).expanduser(), Path(public_path).expanduser()
    if private.resolve() == public.resolve() or private.exists() or public.exists():
        raise ValueError("choose two different, unused filenames")
    if not private.parent.is_dir() or not public.parent.is_dir():
        raise ValueError("destination parent directory missing")
    key = Ed25519PrivateKey.generate()
    secret = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                              serialization.BestAvailableEncryption(password.encode("utf-8")))
    exported = key.public_key().public_bytes(serialization.Encoding.PEM,
                                             serialization.PublicFormat.SubjectPublicKeyInfo)
    _exclusive_write(private, secret)
    try:
        _exclusive_write(public, exported, permission=0o644)
    except BaseException:
        private.unlink(missing_ok=True)
        raise
    return fingerprint(key.public_key())

def load_private_key(path: str | Path, password: str) -> Ed25519PrivateKey:
    data = Path(path).expanduser().read_bytes()
    if len(data) > 16_000:
        raise ValueError("key file too large")
    key = serialization.load_pem_private_key(data, password=password.encode("utf-8"))
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("expected Ed25519 private key")
    return key

def load_public_key(path: str | Path) -> Ed25519PublicKey:
    data = Path(path).expanduser().read_bytes()
    if len(data) > 16_000:
        raise ValueError("trusted public key file too large")
    key = serialization.load_pem_public_key(data)
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("trusted key must be Ed25519")
    return key

def validate_receipt(receipt: object, *, require_local_source: bool = True) -> dict:
    from tools.evie_qualify import EXPECTED_CHECKS, ROOT, SCENARIOS
    if not isinstance(receipt, dict) or receipt.get("schemaVersion") != "evie.qualification-receipt/1":
        raise ValueError("invalid qualification receipt schema")
    module = receipt.get("module")
    if module not in SCENARIOS or receipt.get("scenario") != SCENARIOS[module]["id"]:
        raise ValueError("not an allowlisted qualification scenario")
    if receipt.get("status") != "pass" or receipt.get("origin") != "local-subprocess-observation":
        raise ValueError("only successful local observations can be attested")
    checks = receipt.get("checks")
    if not isinstance(checks, dict) or set(checks) != EXPECTED_CHECKS or any(v is not True for v in checks.values()):
        raise ValueError("receipt checks incomplete")
    policy = receipt.get("effectPolicy", {})
    if (not isinstance(policy, dict) or policy.get("externalEffectsAuthorized") is not False
        or policy.get("networkSandboxEnforced") is not False
        or policy.get("temporaryWorkspace") is not True
        or policy.get("providerEnvironmentStripped") is not True):
        raise ValueError("receipt effect policy unsupported")
    trust = receipt.get("trust", {})
    if not isinstance(trust, dict) or trust.get("signed") is not False or trust.get("authenticatedMachine") is not False:
        raise ValueError("underlying R7 observation must be unsigned and unauthenticated")
    if not isinstance(receipt.get("sourceSha256"), str) or not HEX64.fullmatch(receipt["sourceSha256"]):
        raise ValueError("invalid source digest")
    if not isinstance(receipt.get("artifactSha256"), str) or not HEX64.fullmatch(receipt["artifactSha256"]):
        raise ValueError("invalid output digest")
    if require_local_source:
        source = ROOT / SCENARIOS[module]["source"]
        if receipt["sourceSha256"] != hashlib.sha256(source.read_bytes()).hexdigest():
            raise ValueError("qualification source changed since the run")
    return receipt

def sign_local_receipt(receipt: dict, private_key: Ed25519PrivateKey) -> dict:
    validate_receipt(receipt)
    record = {
        "signedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "receipt": receipt,
    }
    payload = canonical_bytes(record)
    if len(payload) > 64_000:
        raise ValueError("receipt payload too large")
    key = private_key.public_key()
    signature = private_key.sign(DOMAIN + payload)
    return {
        "schemaVersion": SCHEMA,
        "algorithm": "Ed25519",
        "keyFingerprint": fingerprint(key),
        "payloadBase64": base64.b64encode(payload).decode("ascii"),
        "signatureBase64": base64.b64encode(signature).decode("ascii"),
    }

def verify_with_trusted_key(attestation: object, trusted_key: Ed25519PublicKey,
                            *, require_local_source: bool = True) -> dict:
    if not isinstance(attestation, dict) or attestation.get("schemaVersion") != SCHEMA or attestation.get("algorithm") != "Ed25519":
        raise ValueError("unsupported attestation format")
    expected_fingerprint = fingerprint(trusted_key)
    if attestation.get("keyFingerprint") != expected_fingerprint:
        raise ValueError("signer fingerprint differs from explicitly trusted key")
    payload = strict_decode(attestation.get("payloadBase64"), cap=64_000)
    signature = strict_decode(attestation.get("signatureBase64"), cap=64)
    if len(signature) != 64:
        raise ValueError("Ed25519 signature length invalid")
    try:
        trusted_key.verify(signature, DOMAIN + payload)
    except InvalidSignature:
        raise ValueError("signature verification failed") from None
    record = json.loads(payload)
    if not isinstance(record, dict) or set(record) != {"receipt", "signedAt"}:
        raise ValueError("signed record shape invalid")
    if not isinstance(record["signedAt"], str) or not record["signedAt"].endswith("Z"):
        raise ValueError("signed timestamp missing")
    receipt = validate_receipt(record["receipt"], require_local_source=require_local_source)
    return {
        "schemaVersion": "evie.qualification-verification/1",
        "signatureValid": True,
        "trustedKeyFingerprint": expected_fingerprint,
        "module": receipt["module"],
        "scenario": receipt["scenario"],
        "status": receipt["status"],
        "sourceMatched": require_local_source,
        "actionAuthorized": False,
        "trustScope": "signature by independently selected public key; does not prove sandbox isolation or real-world correctness",
    }

def read_attestation(path: str) -> dict:
    file = Path(path).expanduser()
    if file.stat().st_size > MAX_ATTESTATION_BYTES:
        raise ValueError("attestation exceeds 128 KB")
    return json.loads(file.read_text(encoding="utf-8"))

def main() -> int:
    parser = argparse.ArgumentParser(description="Local EVIE key pinning and signed qualification verification.")
    sub = parser.add_subparsers(dest="operation", required=True)
    keygen = sub.add_parser("keygen", help="create encrypted private key and public trust anchor")
    keygen.add_argument("--private", required=True)
    keygen.add_argument("--public", required=True)
    verify = sub.add_parser("verify", help="verify attestation using separately trusted public key")
    verify.add_argument("--attestation", required=True)
    verify.add_argument("--trusted-public", required=True)
    args = parser.parse_args()
    try:
        if args.operation == "keygen":
            password = getpass.getpass("New private-key passphrase (min 12 chars): ")
            again = getpass.getpass("Confirm passphrase: ")
            if password != again:
                raise ValueError("passphrases do not match")
            fp = create_keypair(args.private, args.public, password)
            print(json.dumps({"status": "created", "keyFingerprint": fp, "privateEncrypted": True}))
            return 0
        result = verify_with_trusted_key(read_attestation(args.attestation),
                                         load_public_key(args.trusted_public))
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, TypeError, UnicodeError, json.JSONDecodeError):
        print(json.dumps({"status": "fail", "reason": "key-or-attestation-invalid"}))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
