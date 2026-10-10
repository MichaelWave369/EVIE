"""R16: narrowly scoped, signed LOCAL review-action lease.

Permits one attempted R15 distribution-draft run, never network publishing.
A trusted signing key is selected independently. One-use protection is local
to an intact SQLite ledger on ONE host; this is not a remote trust service,
tamper-proof audit record, host sandbox, or verified human identity.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from tools.evie_attest import canonical_bytes, fingerprint, strict_decode
from app.workflows.preflight import ROOT

SCHEMA = "evie.local-action-lease/1"
DOMAIN = b"EVIE/LOCAL_DISTRIBUTION_LEASE_V1\x00"
ACTION = "local_distribution_draft_only"
WORKFLOW = "local_hooks_to_distribution_review"
HEX64 = re.compile(r"^[a-f0-9]{64}$")
HEX32 = re.compile(r"^[a-f0-9]{32}$")
ENVELOPE_KEYS = {"schemaVersion", "algorithm", "keyFingerprint", "payloadBase64", "signatureBase64"}
BODY_KEYS = {"schemaVersion", "nonce", "action", "workflow", "artifactSha256",
             "sourceSha256", "destinationSha256", "issuedAt", "expiresAt",
             "limits", "externalEffectsAuthorized", "recipientAccepted"}
LIMIT_KEYS = {"maxWallSeconds", "maxArtifactBytes", "maxUses"}
MAX_LEASE_SIZE = 8000


def _stamp(value: str) -> datetime:
    if not isinstance(value, str) or len(value) > 35 or not value.endswith("Z"):
        raise ValueError("UTC Z timestamp required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid UTC timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed.astimezone(timezone.utc)


def _now(now: datetime | None) -> datetime:
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        raise ValueError("timezone-aware instant required")
    return instant.astimezone(timezone.utc)


def destination_sha256(stage_dir: str, *, historical_completed: bool = False) -> str:
    """Bind exact stage dir; historical mode only for read-only post-run inspection.

    Live execution MUST use the default false mode requiring a nonexistent
    destination. Historical mode refuses missing, symlinked or in-repo dirs.
    It is never an authorization to run or stage new files.
    """
    if historical_completed:
        destination = Path(stage_dir).expanduser().absolute()
        if (not destination.is_dir() or destination.is_symlink()
                or destination.resolve().is_relative_to(ROOT.resolve())
                or destination.parent.is_symlink()):
            raise ValueError("completed audit destination must exist outside checkout")
    else:
        from tools.evie_supervised import _stage_directory
        destination = _stage_directory(stage_dir)
    return hashlib.sha256(os.fsencode(str(destination))).hexdigest()


def issue_local_lease(*, artifact_sha: str, source_sha: str, stage_dir: str,
                      private_key: Ed25519PrivateKey,
                      ttl_minutes: int = 5, max_seconds: int = 20,
                      now: datetime | None = None) -> dict:
    if not isinstance(artifact_sha, str) or not HEX64.fullmatch(artifact_sha):
        raise ValueError("invalid artifact SHA")
    if not isinstance(source_sha, str) or not HEX64.fullmatch(source_sha):
        raise ValueError("invalid source SHA")
    if type(ttl_minutes) is not int or not 1 <= ttl_minutes <= 10:
        raise ValueError("lease TTL must be 1–10 minutes")
    if type(max_seconds) is not int or not 1 <= max_seconds <= 20:
        raise ValueError("max seconds must be 1–20")
    now = _now(now)
    body = {
        "schemaVersion": SCHEMA, "nonce": secrets.token_hex(16),
        "action": ACTION, "workflow": WORKFLOW,
        "artifactSha256": artifact_sha, "sourceSha256": source_sha,
        "destinationSha256": destination_sha256(stage_dir),
        "issuedAt": now.isoformat().replace("+00:00", "Z"),
        "expiresAt": (now + timedelta(minutes=ttl_minutes)).isoformat().replace("+00:00", "Z"),
        "limits": {"maxWallSeconds": max_seconds, "maxArtifactBytes": 32768, "maxUses": 1},
        "externalEffectsAuthorized": False, "recipientAccepted": False,
    }
    encoded = canonical_bytes(body)
    return {
        "schemaVersion": SCHEMA,
        "algorithm": "Ed25519",
        "keyFingerprint": fingerprint(private_key.public_key()),
        "payloadBase64": base64.b64encode(encoded).decode("ascii"),
        "signatureBase64": base64.b64encode(private_key.sign(DOMAIN + encoded)).decode("ascii"),
    }


def verify_local_lease(lease: object, trusted_key: Ed25519PublicKey, *,
                       artifact_sha: str, source_sha: str, stage_dir: str,
                       now: datetime | None = None,
                       historical_completed: bool = False) -> dict:
    if type(historical_completed) is not bool:
        raise ValueError("historical inspection flag invalid")
    if not isinstance(lease, dict) or set(lease) != ENVELOPE_KEYS or \
            lease["schemaVersion"] != SCHEMA or lease["algorithm"] != "Ed25519":
        raise ValueError("unsupported signed lease envelope")
    if lease["keyFingerprint"] != fingerprint(trusted_key):
        raise ValueError("lease key is not the independently trusted key")
    payload = strict_decode(lease["payloadBase64"], cap=4000)
    sig = strict_decode(lease["signatureBase64"], cap=64)
    if len(sig) != 64:
        raise ValueError("signature length invalid")
    try:
        trusted_key.verify(sig, DOMAIN + payload)
    except InvalidSignature as exc:
        raise ValueError("lease signature invalid") from exc
    try:
        body = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("signed lease body is not JSON") from exc
    if not isinstance(body, dict) or set(body) != BODY_KEYS or \
            canonical_bytes(body) != payload:
        raise ValueError("lease body has unsupported or noncanonical fields")
    if body["schemaVersion"] != SCHEMA or body["action"] != ACTION or body["workflow"] != WORKFLOW:
        raise ValueError("lease requested an unapproved capability")
    if not isinstance(body["nonce"], str) or not HEX32.fullmatch(body["nonce"]):
        raise ValueError("lease nonce invalid")
    if body["artifactSha256"] != artifact_sha or body["sourceSha256"] != source_sha or \
            body["destinationSha256"] != destination_sha256(stage_dir, historical_completed=historical_completed):
        raise ValueError("signed lease does not match artifact, source or destination")
    if not all(isinstance(x, str) and HEX64.fullmatch(x) for x in
               (body["artifactSha256"], body["sourceSha256"], body["destinationSha256"])):
        raise ValueError("lease digest malformed")
    limits = body["limits"]
    if not isinstance(limits, dict) or set(limits) != LIMIT_KEYS or \
            type(limits["maxUses"]) is not int or limits["maxUses"] != 1 or \
            type(limits["maxWallSeconds"]) is not int or not 1 <= limits["maxWallSeconds"] <= 20 or \
            type(limits["maxArtifactBytes"]) is not int or limits["maxArtifactBytes"] != 32768:
        raise ValueError("lease violates bounded execution policy")
    if body["externalEffectsAuthorized"] is not False or body["recipientAccepted"] is not False:
        raise ValueError("lease cannot grant publishing or recipient authority")
    now = _now(now)
    issued, expires = _stamp(body["issuedAt"]), _stamp(body["expiresAt"])
    if expires <= issued or expires - issued > timedelta(minutes=10) or \
            now < issued - timedelta(seconds=30) or now >= expires:
        raise ValueError("lease not yet valid or expired")
    return body


def load_lease(path: str | Path) -> dict:
    file = Path(path).expanduser()
    if not file.is_file() or file.is_symlink() or file.stat().st_size > MAX_LEASE_SIZE:
        raise ValueError("signed lease must be a small regular file")
    return json.loads(file.read_text(encoding="utf-8"))


def consume_local_lease(body: dict, ledger: str) -> None:
    """Burn nonce atomically BEFORE launching a child. Crash/failed run consumes it.

    Local SQLite locking prevents concurrent reuse if clients share this ledger.
    OS users with write access to the ledger can reset it: no anti-tamper claim.
    """
    path = Path(ledger).expanduser().absolute()
    if path.is_symlink() or path.is_dir() or not path.parent.is_dir() or path.parent.is_symlink():
        raise ValueError("ledger path invalid")
    if path.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("local nonce ledger must stay outside public repo")
    if path.exists() and (not path.is_file() or path.stat().st_size > 2_000_000):
        raise ValueError("nonce ledger invalid or above 2 MB limit")
    # A single ledger file MUST be used for all lease consumers on this host.
    db = sqlite3.connect(str(path), timeout=5, isolation_level=None)
    try:
        if os.name != "nt":
            os.chmod(path, 0o600)
        db.execute("PRAGMA busy_timeout=5000")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("BEGIN IMMEDIATE")
        db.execute("CREATE TABLE IF NOT EXISTS spent_local_leases (nonce TEXT PRIMARY KEY, artifact TEXT NOT NULL, spent_at TEXT NOT NULL)")
        db.execute(
            "INSERT INTO spent_local_leases (nonce,artifact,spent_at) VALUES (?,?,?)",
            (body["nonce"], body["artifactSha256"],
             datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")),
        )
        db.execute("COMMIT")
    except (sqlite3.Error, OSError) as exc:
        if db.in_transaction:
            db.execute("ROLLBACK")
        raise ValueError("lease already used, ledger blocked or unavailable") from exc
    finally:
        db.close()
