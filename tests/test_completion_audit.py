"""R20: read-only evidence chain and explicit legacy execution exposure."""
import hashlib
import json
from pathlib import Path

import pytest
from tools import evie_completion_audit as audit
from tools import evie_governed_flow as flow
from tools import evie_hooks_container as hooks_capsule
from tools import evie_container_runner as container
from tools import evie_isolated_distribution as isolated
from tools import evie_supervised_hooks as hooks
from tools import evie_supervised_distribution as distribution
from tools.evie_attest import create_keypair, load_private_key
from tools.evie_action_lease_contract import issue_local_lease

SCRIPT = ("The creator drafts nine review-only hooks based on source notes. "
          "A signed local action authorizes one offline draft attempt but cannot "
          "approve publication or bypass editorial checking.\n")
PASSPHRASE = "test-encrypted-lease-signing-key-password"


@pytest.fixture
def paused(tmp_path, monkeypatch):
    # Normal suite simulates container backend but calls real original producer.
    # This is NOT independent sandbox proof; dedicated Docker CI covers that.
    monkeypatch.setattr(hooks_capsule, "image_preflight",
                        lambda: "sha256:" + "a"*64)
    monkeypatch.setattr(hooks_capsule, "run_hooks_isolated",
                        lambda title, script, seconds, *, image_id:
                        hooks.subprocess_run(title, script, seconds))
    text = tmp_path / "script.txt"
    text.write_text(SCRIPT, encoding="utf-8")
    folder = tmp_path / "session"
    event = flow.start_session(
        session_dir=str(folder), script_file=str(text),
        topic="EVIE Creator Loop", confirm=True)
    return folder, event


@pytest.fixture
def staged(paused, tmp_path, monkeypatch):
    folder, event = paused
    monkeypatch.setattr(container, "image_preflight",
                        lambda: "sha256:" + "b"*64)
    monkeypatch.setattr(isolated, "image_preflight",
                        lambda: "sha256:" + "b"*64)
    monkeypatch.setattr(isolated, "run_isolated",
                        lambda topic, lines, timeout, *, image_id:
                        distribution._run_second_step(topic, lines, timeout))
    private, trusted = tmp_path / "signing.pem", tmp_path / "trusted.pem"
    create_keypair(str(private), str(trusted), PASSPHRASE)
    key = load_private_key(private, PASSPHRASE)
    lease = issue_local_lease(
        artifact_sha=event["hooksArtifactSha256"],
        source_sha=event["workflowSourceSha256"],
        stage_dir=str(folder / "distribution"),
        private_key=key,
    )
    lease_file = tmp_path / "approval.lease.json"
    lease_file.write_text(json.dumps(lease), encoding="utf-8")
    ledger = tmp_path / "nonce-ledger.sqlite"
    result = flow.resume_session(
        session_dir=str(folder), lease_file=str(lease_file),
        trusted_public=str(trusted), ledger=str(ledger), confirm=True)
    assert result["state"] == flow.STATES[2]
    return folder, lease_file, trusted, ledger


def test_entrypoint_exposure_report_identifies_unprotected_legacy_lanes():
    report = audit.source_exposure()
    assert report["report"] == "known_entrypoint_inventory"
    assert report["allRepositoryPathsEnforced"] is False
    assert report["hostRuntimeProbed"] is False
    assert len(report["sourceFiles"]) == 6
    lanes = {item["id"]:item for item in report["sourceFiles"]}
    assert lanes["legacy_host_hooks"]["hostExecutionPossible"] is True
    assert lanes["legacy_hash_distribution"]["signedLeaseRequiredByThisCommand"] is False
    assert lanes["legacy_signed_distribution"]["dockerRequiredByThisCommand"] is False
    assert lanes["preferred_dual_capsule_controller"]["dockerRequiredByThisCommand"] is True
    for lane in lanes.values():
        assert hashlib.sha256(
            (audit.ROOT / lane["entrypoint"]).read_bytes()
        ).hexdigest() == lane["sourceSha256"]


def test_paused_remains_review_only_and_auditor_creates_no_files(paused):
    folder, _ = paused
    before = {str(p):p.stat().st_mtime_ns for p in folder.rglob("*") if p.is_file()}
    result = audit.audit_session(str(folder))
    after = {str(p):p.stat().st_mtime_ns for p in folder.rglob("*") if p.is_file()}
    assert before == after
    assert result["sessionState"] == "paused_for_human_review"
    assert result["completionContract"]["status"] == "WAITING_FOR_REVIEW"
    assert result["completionContract"]["fullyVerified"] is False
    assert result["policy"]["finalProductDone"] is False
    assert result["policy"]["publishingAuthorized"] is False


def test_unknown_attempt_never_qualifies_as_complete(paused):
    folder, first = paused
    flow._emit(folder, flow.EVENT_2, {
        "schemaVersion": flow.SCHEMA, "event": "signed_resume_attempt",
        "state": flow.STATES[1], "sessionNonce": first["sessionNonce"],
        "leaseNonce": "b"*32, "approvedHooksSha256": first["hooksArtifactSha256"],
        "stageTwoExecutionAttempted": True, "externalPublishingAuthorized": False,
        "editorialApprovalGranted": False,
    })
    report = audit.audit_session(str(folder))
    assert report["completionContract"]["status"] == "ATTEMPT_OUTCOME_UNKNOWN"
    assert report["completionContract"]["fullyVerified"] is False
    assert report["policy"]["automaticRetryAllowed"] is False


def test_complete_narrow_draft_evidence_with_signature_and_read_only_nonce_ledger(staged):
    folder, lease, key, ledger = staged
    before = {str(p):p.stat().st_mtime_ns for p in folder.rglob("*") if p.is_file()}
    ledger_mtime = ledger.stat().st_mtime_ns
    result = audit.audit_session(
        str(folder), lease_file=str(lease),
        trusted_public=str(key), ledger=str(ledger))
    assert result["completionContract"]["status"] == "LOCAL_DRAFT_CONTRACT_VERIFIED"
    assert result["completionContract"]["fullyVerified"] is True
    assert result["authorization"]["historicalLeaseSignatureValid"] is True
    assert result["authorization"]["singleHostLedgerNonceFound"] is True
    assert result["authorization"]["realWorldOperatorIdentityAuthenticated"] is False
    assert result["policy"]["finalProductDone"] is False
    assert result["policy"]["editorialAcceptanceVerified"] is False
    assert result["policy"]["publishingAuthorized"] is False
    assert ledger.stat().st_mtime_ns == ledger_mtime
    assert before == {str(p):p.stat().st_mtime_ns for p in folder.rglob("*") if p.is_file()}


def test_staged_artifacts_are_not_fully_verified_without_independent_trust(staged):
    folder, _, _, _ = staged
    report = audit.audit_session(str(folder))
    assert report["completionContract"]["status"] == "DRAFT_STAGED_APPROVAL_UNVERIFIED"
    assert report["completionContract"]["fullyVerified"] is False


def test_tampered_hook_file_or_forged_publishing_status_rejected(staged):
    folder, *_ = staged
    receipt_path = folder/"distribution"/"distribution-review-receipt.json"
    original = receipt_path.read_bytes()
    receipt = json.loads(original)
    receipt["governance"]["externalPublishing"] = True
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="forbidden effects"):
        audit.audit_session(str(folder))
    receipt_path.write_bytes(original)
    hook_file = folder/"hooks"/"nine-hooks.json"
    hook_file.write_bytes(hook_file.read_bytes() + b" ")
    with pytest.raises(ValueError):
        audit.audit_session(str(folder))


def test_untrusted_key_or_missing_spent_ledger_refused_without_creating_it(staged, tmp_path):
    folder, lease, _, ledger = staged
    with pytest.raises(ValueError, match="supplied together"):
        audit.audit_session(str(folder), lease_file=str(lease))
    no_ledger = tmp_path / "missing.sqlite"
    with pytest.raises(ValueError, match="ledger unavailable"):
        audit.audit_session(str(folder), lease_file=str(lease),
                            trusted_public=str(staged[2]), ledger=str(no_ledger))
    assert not no_ledger.exists()
    private, public = tmp_path / "other.pem", tmp_path / "otherpub.pem"
    create_keypair(str(private), str(public), PASSPHRASE)
    with pytest.raises(ValueError, match="independently trusted"):
        audit.audit_session(str(folder), lease_file=str(lease),
                            trusted_public=str(public), ledger=str(ledger))


def test_original_execution_lease_still_rejects_existing_stage_directory(staged):
    folder, lease, key, _ = staged
    from tools.evie_action_lease_contract import load_lease, verify_local_lease
    from tools.evie_attest import load_public_key
    data = load_lease(lease)
    first = json.loads((folder/flow.EVENT_1).read_text())
    # Regular execution verification remains default-deny for existing dirs.
    with pytest.raises(ValueError, match="exists"):
        verify_local_lease(data, load_public_key(key),
                           artifact_sha=first["hooksArtifactSha256"],
                           source_sha=first["workflowSourceSha256"],
                           stage_dir=str(folder/"distribution"))
