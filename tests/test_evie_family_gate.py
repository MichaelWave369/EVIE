"""EVIE R8B family artifacts: no transport, signed review, explicit limits."""
import base64
import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest

from app.family_gate.contracts import (
    TARGETS, PROPOSAL_SCHEMA, ACK_SCHEMA, MAX_ARTIFACT, acknowledge,
    catalog, create_proposal, hash_local_artifact, validate_proposal,
    verify_acknowledgement,
)
from tools.evie_attest import create_keypair, load_private_key, load_public_key
from tools.evie_family_gate import save_new, read_json_file

@pytest.fixture()
def keys(tmp_path):
    private, public = tmp_path/"family-private.pem", tmp_path/"family-public.pem"
    create_keypair(str(private), str(public), "an-independent-passphrase")
    return (load_private_key(private, "an-independent-passphrase"), load_public_key(public))

@pytest.fixture()
def proposal():
    return create_proposal(
        "openblueprint.evie-proposal/1", "openblue", "a"*64, 120,
        now=datetime(2026, 10, 9, 18, 0, tzinfo=timezone.utc),
    )

def test_catalog_6_intended_destinations_but_zero_transports():
    data = catalog()
    assert set(TARGETS) == {i["id"] for i in data["targets"]}
    assert len(data["targets"]) == 6
    assert all(p["transport"] == "not-implemented" and p["execution"] == "disabled"
               for p in data["targets"])

def test_proposal_constrains_targets_digests_lifetime_and_effects(proposal):
    when = datetime(2026, 10, 9, 18, 1, tzinfo=timezone.utc)
    assert validate_proposal(proposal, now=when)["schemaVersion"] == PROPOSAL_SCHEMA
    for updates in (
        {"target": "gmail"},
        {"artifactKind": "executable/python"},
        {"requestedEffects": ["publish"]},
        {"executionAuthorized": True},
        {"transportEnabled": True},
        {"artifactSha256": "not-a-digest"},
        {"artifactBytes": MAX_ARTIFACT + 1},
        {"nonce": "../escape"},
        {"extra": "no"},
    ):
        with pytest.raises(ValueError):
            validate_proposal({**proposal, **updates}, now=when)
    with pytest.raises(ValueError, match="expired"):
        validate_proposal(proposal, now=when + timedelta(hours=2))
    with pytest.raises(ValueError):
        create_proposal("openblueprint.evie-proposal/1", "openblue", "a"*64, 120, ttl_minutes=90)
    assert proposal["requestedEffects"] == []

def test_approved_local_review_does_not_grant_transport_or_execution(proposal, keys):
    key, public = keys
    acknowledged = acknowledge(proposal, key, now=datetime(2026, 10, 9, 18, 1, tzinfo=timezone.utc))
    assert acknowledged["schemaVersion"] == ACK_SCHEMA
    result = verify_acknowledgement(acknowledged, public,
                                    now=datetime(2026, 10, 9, 18, 2, tzinfo=timezone.utc))
    assert result["signatureValid"] is True
    assert result["reviewAcknowledged"] is True
    assert result["executionAuthorized"] is False
    assert result["transportEnabled"] is False
    assert result["oneTimeConsumptionEnforced"] is False

def test_different_key_tampering_and_expiry_fail(proposal, keys, tmp_path):
    private, trusted = keys
    signed = acknowledge(proposal, private, now=datetime(2026, 10, 9, 18, 2, tzinfo=timezone.utc))
    other_prv, other_pub = tmp_path/"other.pem", tmp_path/"other.pub.pem"
    create_keypair(str(other_prv), str(other_pub), "another-private-passphrase")
    with pytest.raises(ValueError, match="trusted public key differs"):
        verify_acknowledgement(signed, load_public_key(other_pub),
                               now=datetime(2026, 10, 9, 18, 2, tzinfo=timezone.utc))
    original = json.loads(base64.b64decode(signed["payloadBase64"]))
    original["proposal"]["artifactSha256"] = "b"*64
    forged = {**signed, "payloadBase64": base64.b64encode(json.dumps(original).encode()).decode()}
    with pytest.raises(ValueError, match="invalid acknowledgement signature"):
        verify_acknowledgement(forged, trusted,
                               now=datetime(2026, 10, 9, 18, 2, tzinfo=timezone.utc))
    with pytest.raises(ValueError, match="expired"):
        verify_acknowledgement(signed, trusted,
                               now=datetime(2026, 10, 9, 19, 0, tzinfo=timezone.utc))

def test_artifact_hash_and_explicit_nonoverwriting_output(tmp_path, proposal):
    artifact=tmp_path/"proposal.json"
    artifact.write_bytes(b"some harmless artifact bytes")
    sha, size=hash_local_artifact(str(artifact))
    assert sha == hashlib.sha256(b"some harmless artifact bytes").hexdigest()
    assert size == len(b"some harmless artifact bytes")
    path=tmp_path/"handoff.json"
    save_new(str(path), proposal)
    assert read_json_file(str(path))["target"] == "openblue"
    with pytest.raises(FileExistsError):
        save_new(str(path), proposal)
    (tmp_path/"link.json").symlink_to(artifact)
    with pytest.raises(ValueError):
        hash_local_artifact(str(tmp_path/"link.json"))
