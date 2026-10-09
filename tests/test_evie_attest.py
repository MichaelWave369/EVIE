"""R8 local Ed25519 attestation and explicitly pinned trust-root tests."""
import base64
import json
from pathlib import Path

import pytest

from tools.evie_attest import (
    SCHEMA, DOMAIN, canonical_bytes, create_keypair, fingerprint,
    load_private_key, load_public_key, sign_local_receipt, validate_receipt,
    verify_with_trusted_key, _exclusive_write, read_attestation,
)
from tools.evie_qualify import run_qualification

@pytest.fixture()
def signer(tmp_path):
    prv = tmp_path / "evie-signing.pem"
    pub = tmp_path / "evie-pinned.pub.pem"
    fp = create_keypair(str(prv), str(pub), "local-demo-phrase-long-enough")
    return prv, pub, fp

@pytest.fixture()
def good_receipt():
    report = run_qualification("openblueprint_floor_plan")
    assert report["status"] == "pass"
    return report

def test_encrypted_private_key_and_explicit_public_key(signer):
    private, public, fp = signer
    assert b"ENCRYPTED PRIVATE KEY" in private.read_bytes()
    assert b"PRIVATE KEY" not in public.read_bytes()
    assert fingerprint(load_public_key(public)) == fp
    with pytest.raises((TypeError, ValueError)):
        load_private_key(private, "wrong-passphrase")
    with pytest.raises(ValueError):
        create_keypair(str(private), str(public), "local-demo-phrase-long-enough")
    with pytest.raises(ValueError):
        create_keypair(str(private.parent/"short.pem"), str(private.parent/"short.pub.pem"), "short")

def test_signed_actual_local_fixture_verifies_with_pinned_key(signer, good_receipt):
    private, public, fp = signer
    key = load_private_key(private, "local-demo-phrase-long-enough")
    attested = sign_local_receipt(good_receipt, key)
    assert attested["schemaVersion"] == SCHEMA
    assert attested["keyFingerprint"] == fp
    assert "passphrase" not in json.dumps(attested).lower()
    output = verify_with_trusted_key(attested, load_public_key(public))
    assert output["signatureValid"] is True
    assert output["status"] == "pass"
    assert output["sourceMatched"] is True
    assert output["actionAuthorized"] is False
    assert output["module"] == "openblueprint_floor_plan"
    assert good_receipt["trust"]["signed"] is False
    output_path = private.parent / "run.attestation.json"
    _exclusive_write(output_path, (json.dumps(attested) + "\n").encode("utf-8"))
    assert read_attestation(str(output_path)) == attested
    with pytest.raises(FileExistsError):
        _exclusive_write(output_path, b"attempted-overwrite")

def test_wrong_trust_root_and_payload_tampering_fail(signer, good_receipt, tmp_path):
    private, public, _ = signer
    att = sign_local_receipt(good_receipt, load_private_key(private, "local-demo-phrase-long-enough"))
    other_private = tmp_path / "other.pem"
    other_public = tmp_path / "other.pub.pem"
    create_keypair(str(other_private), str(other_public), "another-very-long-private-passphrase")
    with pytest.raises(ValueError, match="fingerprint differs"):
        verify_with_trusted_key(att, load_public_key(other_public))
    payload = json.loads(base64.b64decode(att["payloadBase64"]))
    payload["receipt"]["durationMs"] += 1
    modified = {**att, "payloadBase64": base64.b64encode(canonical_bytes(payload)).decode("ascii")}
    with pytest.raises(ValueError, match="signature verification failed"):
        verify_with_trusted_key(modified, load_public_key(public))
    forged = {**att, "signatureBase64": base64.b64encode(bytes(64)).decode("ascii")}
    with pytest.raises(ValueError, match="signature verification failed"):
        verify_with_trusted_key(forged, load_public_key(public))

def test_cannot_attest_failed_unsigned_or_mismatched_source(signer, good_receipt):
    private, _, _ = signer
    key = load_private_key(private, "local-demo-phrase-long-enough")
    for changes in [
        {"status": "fail"},
        {"sourceSha256": "a" * 64},
        {"checks": {"digest_match": True}},
        {"effectPolicy": {**good_receipt["effectPolicy"], "externalEffectsAuthorized": True}},
        {"module": "youtube_publisher"},
        {"trust": {**good_receipt["trust"], "signed": True}},
    ]:
        with pytest.raises(ValueError):
            sign_local_receipt({**good_receipt, **changes}, key)

def test_signature_domain_separation_and_unique_file(signer, good_receipt):
    private, public, _ = signer
    att = sign_local_receipt(good_receipt, load_private_key(private, "local-demo-phrase-long-enough"))
    decoded = base64.b64decode(att["payloadBase64"])
    assert decoded.startswith(b"{")
    assert DOMAIN.startswith(b"EVIE/")
    # Signature covers a domain prefix and the canonical record, not just the JSON bytes.
    with pytest.raises(Exception):
        load_public_key(public).verify(base64.b64decode(att["signatureBase64"]), decoded)
    assert verify_with_trusted_key(att, load_public_key(public))["signatureValid"]
