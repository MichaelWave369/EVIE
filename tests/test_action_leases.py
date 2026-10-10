"""R16 signed local action leases, real gated R15 run and replay-denial tests."""
from __future__ import annotations
import base64
import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from tools.evie_attest import create_keypair, load_private_key, load_public_key
from tools import evie_supervised_hooks as hooks
from tools import evie_supervised_distribution as dist
from tools.evie_action_lease_contract import (
    SCHEMA, issue_local_lease, verify_local_lease, consume_local_lease,
    destination_sha256,
)
from tools.evie_approved_distribution import run_with_local_lease

SCRIPT = ("EVIE's source-only workflow registry supports supervised content drafting. "
          "Generated hooks require manual inspection and fact checking. "
          "A local review receipt does not authorize publishing.\n")
PASS = "local-action-signing-key-long-passphrase"

@pytest.fixture
def operator(tmp_path):
    private = tmp_path / "signing.pem"
    public = tmp_path / "trusted-public.pem"
    create_keypair(str(private), str(public), PASS)
    return private, public, load_private_key(private, PASS), load_public_key(public)

@pytest.fixture
def first(tmp_path):
    file = tmp_path / "draft.txt"
    file.write_text(SCRIPT, encoding="utf-8")
    directory = tmp_path / "hooks"
    receipt = hooks.stage_hooks(
        script_file=str(file), topic="EVIE Creator Loop",
        stage_dir=str(directory), confirm=True)
    source_sha = dist._source_check()[1]
    assert receipt["workflowSourceSha256"] == source_sha
    return directory, receipt, source_sha

def sign(operator, first, destination, **kwargs):
    _, _, key, _ = operator
    _, receipt, source = first
    return issue_local_lease(
        artifact_sha=receipt["artifactSha256"], source_sha=source,
        stage_dir=str(destination), private_key=key, **kwargs)

def test_signed_lease_and_real_supervised_execution_single_use(tmp_path, first, operator):
    folder, receipt, source = first
    stage = tmp_path / "review-stage-2"
    lease = sign(operator, first, stage)
    trusted_file = operator[1]
    file = tmp_path / "approved.lease.json"
    file.write_text(json.dumps(lease), encoding="utf-8")
    ledger = tmp_path / "leases.sqlite"
    result = run_with_local_lease(
        hooks_dir=str(folder), approved_hooks_sha256=receipt["artifactSha256"],
        stage_dir=str(stage), lease_file=str(file),
        trusted_public=str(trusted_file), ledger=str(ledger), confirm=True)
    assert result["status"] == "second-stage-staged"
    assert result["approvalSignatureVerified"] is True
    assert result["localNonceConsumed"] is True
    assert result["signedExecutionReceipt"] is False
    assert result["publishingAuthorized"] is False
    assert result["recipientAccepted"] is False
    assert len(list(stage.iterdir())) == 4
    assert json.loads((stage / "lease-consumption.json").read_text()) == result
    output = json.loads((stage / "distribution-draft.json").read_text())
    src = json.loads((folder / "nine-hooks.json").read_text())
    assert output["hooks_used"] == src["hooks"][:5]
    with sqlite3.connect(ledger) as db:
        spent = db.execute("SELECT nonce,artifact FROM spent_local_leases").fetchall()
    assert spent == [(result["nonce"], receipt["artifactSha256"])]
    with pytest.raises(ValueError, match="lease already used"):
        consume_local_lease(json.loads(base64.b64decode(lease["payloadBase64"])), str(ledger))

def test_scope_wrong_destination_source_and_artifact_are_denied(tmp_path, first, operator):
    _, receipt, source = first
    folder = tmp_path / "stage"
    lease = sign(operator, first, folder)
    _, _, _, trusted = operator
    kw = {"artifact_sha": receipt["artifactSha256"], "source_sha": source,
          "stage_dir": str(folder)}
    verify_local_lease(lease, trusted, **kw)
    with pytest.raises(ValueError, match="artifact, source or destination"):
        verify_local_lease(lease, trusted, **{**kw,"stage_dir":str(tmp_path/"other")})
    with pytest.raises(ValueError, match="artifact, source or destination"):
        verify_local_lease(lease, trusted, **{**kw,"artifact_sha":"a"*64})
    with pytest.raises(ValueError, match="artifact, source or destination"):
        verify_local_lease(lease, trusted, **{**kw,"source_sha":"b"*64})

def test_expiry_future_ttl_and_budget_fail_closed(tmp_path, first, operator):
    stage = tmp_path / "stage"
    _, r, source = first
    t = datetime(2026,10,9,20,0,tzinfo=timezone.utc)
    lease = sign(operator, first, stage, now=t, ttl_minutes=1, max_seconds=6)
    kw = dict(artifact_sha=r["artifactSha256"],source_sha=source,stage_dir=str(stage))
    body = verify_local_lease(lease, operator[3], now=t+timedelta(seconds=30), **kw)
    assert body["limits"]["maxWallSeconds"] == 6
    with pytest.raises(ValueError, match="expired"):
        verify_local_lease(lease, operator[3], now=t+timedelta(minutes=2), **kw)
    with pytest.raises(ValueError, match="not yet"):
        verify_local_lease(lease, operator[3], now=t-timedelta(minutes=1), **kw)
    with pytest.raises(ValueError, match="TTL"):
        sign(operator, first, stage, now=t, ttl_minutes=11)
    with pytest.raises(ValueError, match="max seconds"):
        sign(operator, first, stage, now=t, max_seconds=21)

def test_signature_domain_and_independent_key_tampering(tmp_path, first, operator):
    stage = tmp_path / "stage"
    lease=sign(operator,first,stage)
    folder,r,source=first
    kw=dict(artifact_sha=r["artifactSha256"],source_sha=source,stage_dir=str(stage))
    otherprivate=tmp_path / "other.pem"
    otherpublic=tmp_path / "other.pub.pem"
    create_keypair(str(otherprivate),str(otherpublic),PASS)
    with pytest.raises(ValueError, match="independently trusted"):
        verify_local_lease(lease,load_public_key(otherpublic),**kw)
    payload=json.loads(base64.b64decode(lease["payloadBase64"]))
    payload["externalEffectsAuthorized"]=True
    tampered={**lease,"payloadBase64":base64.b64encode(
        json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).decode()}
    with pytest.raises(ValueError, match="signature"):
        verify_local_lease(tampered,operator[3],**kw)
    with pytest.raises(ValueError):
        verify_local_lease({**lease,"actionAuthorized":True},operator[3],**kw)

def test_concurrent_nonce_consume_is_atomic_for_shared_local_ledger(tmp_path, first, operator):
    lease=sign(operator,first,tmp_path/"stage")
    folder,r,source=first
    body=verify_local_lease(lease,operator[3],artifact_sha=r["artifactSha256"],
                            source_sha=source,stage_dir=str(tmp_path/"stage"))
    ledger=str(tmp_path/"spent.sqlite")
    def attempt(_):
        try:
            consume_local_lease(body, ledger)
            return True
        except ValueError:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(attempt,range(2)))
    assert sorted(results)==[False,True]
    with sqlite3.connect(ledger) as db:
        assert db.execute("SELECT COUNT(*) FROM spent_local_leases").fetchone()[0]==1

def test_bad_lease_does_not_create_ledger_or_run(tmp_path, first, operator):
    folder,receipt,source=first
    stage=tmp_path/"stage"
    lease=sign(operator,first,stage)
    file=tmp_path/"lease.json"
    file.write_text(json.dumps(lease))
    ledger=tmp_path/"spent.sqlite"
    with pytest.raises(ValueError, match="explicitly confirmed"):
        run_with_local_lease(hooks_dir=str(folder),approved_hooks_sha256=receipt["artifactSha256"],
            stage_dir=str(stage),lease_file=str(file),trusted_public=str(operator[1]),
            ledger=str(ledger),confirm=False)
    assert not stage.exists() and not ledger.exists()
    short_lease = sign(operator, first, stage, max_seconds=5)
    file.write_text(json.dumps(short_lease))
    with pytest.raises(ValueError, match="signed budget"):
        run_with_local_lease(hooks_dir=str(folder), approved_hooks_sha256=receipt["artifactSha256"],
            stage_dir=str(stage), lease_file=str(file), trusted_public=str(operator[1]),
            ledger=str(ledger), confirm=True, timeout=20)
    # Verify malformed trust does not burn the lease.
    with pytest.raises(ValueError, match="independently trusted"):
        other=tmp_path/"otherpub.pem"
        wrongprivate=tmp_path/"wrongprivate.pem"
        create_keypair(str(wrongprivate),str(other),PASS)
        run_with_local_lease(hooks_dir=str(folder),approved_hooks_sha256=receipt["artifactSha256"],
            stage_dir=str(stage),lease_file=str(file),trusted_public=str(other),
            ledger=str(ledger),confirm=True)
    assert not ledger.exists()
