"""EVIE family handoff review contract. No transport, executor or action authorization."""
from __future__ import annotations

import base64
import hashlib
import json
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from tools.evie_attest import canonical_bytes, fingerprint, strict_decode

PROPOSAL_SCHEMA = "evie.family-handoff-proposal/1"
ACK_SCHEMA = "evie.family-handoff-acknowledgement/1"
DOMAIN = b"EVIE/FAMILY_HANDOFF_ACK_V1\x00"
SHA = re.compile(r"^[a-f0-9]{64}$")
MAX_ARTIFACT = 8 * 1024 * 1024
_catalog_file = Path(__file__).with_name("family_targets.json")
_REVIEW_CATALOG = json.loads(_catalog_file.read_text(encoding="utf-8"))
if _REVIEW_CATALOG.get("schemaVersion") != "evie.family-target-catalog/1":
    raise ValueError("unknown family target catalog")
TARGETS = {t["id"]: tuple(t["artifactKinds"]) for t in _REVIEW_CATALOG["targets"]}
# These are intended exchange contracts, NOT available recipient implementations.
PROPOSAL_KEYS = frozenset({
    "schemaVersion", "source", "target", "artifactKind", "artifactSha256",
    "artifactBytes", "intent", "nonce", "createdAt", "expiresAt",
    "requestedEffects", "executionAuthorized", "transportEnabled",
})

def catalog() -> dict:
    return {
        **_REVIEW_CATALOG,
        "targets": [{**entry,
                     "transport": "not-implemented", "execution": "disabled",
                     "capabilityStatus": "proposed-contract-only"}
                    for entry in _REVIEW_CATALOG["targets"]],
    }

def _stamp(value: str) -> datetime:
    if not isinstance(value, str) or len(value) > 35:
        raise ValueError("invalid timestamp")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if dt.tzinfo is None:
        raise ValueError("UTC timestamp required")
    return dt.astimezone(timezone.utc)

def validate_proposal(value: Any, *, now: datetime | None = None) -> dict:
    if not isinstance(value, dict) or set(value) != PROPOSAL_KEYS:
        raise ValueError("handoff proposal has unsupported/missing fields")
    if value["schemaVersion"] != PROPOSAL_SCHEMA or value["source"] != "EVIE":
        raise ValueError("source or schema invalid")
    target = value["target"]
    if not isinstance(target, str) or target not in TARGETS or value["artifactKind"] not in TARGETS[target]:
        raise ValueError("target/artifact pairing not in reviewed catalog")
    if (not isinstance(value["artifactSha256"], str) or
            SHA.fullmatch(value["artifactSha256"]) is None):
        raise ValueError("artifact SHA-256 malformed")
    size = value["artifactBytes"]
    if type(size) is not int or not 0 < size <= MAX_ARTIFACT:
        raise ValueError("artifact size invalid or over 8 MB")
    if value["intent"] != "manual_inspection_only":
        raise ValueError("unsupported intent")
    if value["requestedEffects"] != [] or value["executionAuthorized"] is not False or value["transportEnabled"] is not False:
        raise ValueError("proposal cannot request effects or execution")
    nonce = value["nonce"]
    if not isinstance(nonce, str) or not re.fullmatch(r"[a-f0-9]{32}", nonce):
        raise ValueError("proposal nonce invalid")
    created, expires = _stamp(value["createdAt"]), _stamp(value["expiresAt"])
    if not timedelta(seconds=0) < expires - created <= timedelta(minutes=30):
        raise ValueError("proposal TTL exceeds 30 minutes")
    current = now or datetime.now(timezone.utc)
    if current - timedelta(minutes=2) > expires:
        raise ValueError("proposal has expired")
    if created > current + timedelta(minutes=2):
        raise ValueError("proposal timestamp in future")
    return value

def create_proposal(kind: str, target: str, digest: str, size: int, *,
                    ttl_minutes: int = 15, now: datetime | None = None) -> dict:
    if type(ttl_minutes) is not int or not 1 <= ttl_minutes <= 30:
        raise ValueError("TTL must be between 1 and 30 minutes")
    when = now or datetime.now(timezone.utc)
    proposal = {
        "schemaVersion": PROPOSAL_SCHEMA, "source": "EVIE",
        "target": target, "artifactKind": kind, "artifactSha256": digest,
        "artifactBytes": size, "intent": "manual_inspection_only",
        "nonce": secrets.token_hex(16),
        "createdAt": when.isoformat().replace("+00:00", "Z"),
        "expiresAt": (when + timedelta(minutes=ttl_minutes)).isoformat().replace("+00:00", "Z"),
        "requestedEffects": [], "executionAuthorized": False, "transportEnabled": False,
    }
    return validate_proposal(proposal, now=when)

def hash_local_artifact(filename: str) -> tuple[str, int]:
    path = Path(filename).expanduser()
    if not path.is_file() or path.is_symlink():
        raise ValueError("artifact file must be a regular file")
    size = path.stat().st_size
    if not 0 < size <= MAX_ARTIFACT:
        raise ValueError("file empty or exceeds 8 MB")
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            digest.update(block)
    if path.stat().st_size != size:
        raise ValueError("artifact changed during hashing")
    return digest.hexdigest(), size

def acknowledge(proposal: dict, key: Ed25519PrivateKey, *, now: datetime | None = None) -> dict:
    # Explicit signer action only, not a job grant.
    proposal = validate_proposal(proposal, now=now)
    payload = canonical_bytes({"proposal": proposal, "decision": "reviewed-for-manual-handoff",
                               "actionAuthorized": False})
    if len(payload) > 20_000:
        raise ValueError("proposal too large")
    signature = key.sign(DOMAIN + payload)
    return {
        "schemaVersion": ACK_SCHEMA, "algorithm": "Ed25519",
        "keyFingerprint": fingerprint(key.public_key()),
        "payloadBase64": base64.b64encode(payload).decode("ascii"),
        "signatureBase64": base64.b64encode(signature).decode("ascii"),
    }

def verify_acknowledgement(ack: Any, trusted_key: Ed25519PublicKey,
                           *, now: datetime | None = None) -> dict:
    if not isinstance(ack, dict) or set(ack) != {
        "schemaVersion", "algorithm", "keyFingerprint", "payloadBase64", "signatureBase64"
    } or ack["schemaVersion"] != ACK_SCHEMA or ack["algorithm"] != "Ed25519":
        raise ValueError("invalid acknowledgement envelope")
    expected = fingerprint(trusted_key)
    if ack["keyFingerprint"] != expected:
        raise ValueError("independently trusted public key differs")
    raw = strict_decode(ack["payloadBase64"], cap=20_000)
    sig = strict_decode(ack["signatureBase64"], cap=64)
    if len(sig) != 64:
        raise ValueError("wrong Ed25519 signature length")
    try:
        trusted_key.verify(sig, DOMAIN + raw)
    except InvalidSignature:
        raise ValueError("invalid acknowledgement signature") from None
    body = json.loads(raw)
    if not isinstance(body, dict) or set(body) != {"proposal", "decision", "actionAuthorized"}:
        raise ValueError("signed body malformed")
    if body["decision"] != "reviewed-for-manual-handoff" or body["actionAuthorized"] is not False:
        raise ValueError("signed decision cannot grant execution")
    p = validate_proposal(body["proposal"], now=now)
    return {
        "schemaVersion": "evie.family-handoff-verification/1",
        "signatureValid": True, "trustedKeyFingerprint": expected,
        "target": p["target"], "artifactKind": p["artifactKind"],
        "artifactSha256": p["artifactSha256"], "expiresAt": p["expiresAt"],
        "reviewAcknowledged": True, "transportEnabled": False,
        "executionAuthorized": False, "oneTimeConsumptionEnforced": False,
        "note": "Key holder acknowledged this envelope. Not evidence of receipt by recipient or permission to act.",
    }
