"""R18: governed real two-step session, pause, explicit signing, no replay.

The default test suite exercises actual R14 hooks and actual v2 distribution
code, with Docker substituted by a mock *only in the normal test lane*. The
separate EVIE_TEST_DOCKER CI lane runs the real signed Docker backend end to end.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from tools.evie_attest import create_keypair, load_private_key
from tools.evie_action_lease_contract import issue_local_lease
from tools import evie_governed_flow as flow
from tools import evie_supervised_distribution as distribution
from tools import evie_isolated_distribution as isolated
from tools import evie_container_runner as capsule
from tools import evie_hooks_container as hooks_capsule
from tools import evie_completion_audit as completion_audit
from tools import evie_supervised_hooks as legacy_hooks

SCRIPT = ("EVIE should create real draft hooks from these notes before review. "
          "No automation may publish or approve marketing claims by itself. "
          "Only an operator-selected and signed local execution can continue.\n")
PASSWORD = "encrypted-key-test-passphrase"


@pytest.fixture
def started(tmp_path, monkeypatch):
    # Normal tests run the REAL producer in host Python, but mock Docker ONLY
    # when EVIE_TEST_DOCKER is absent. Real Docker CI does not mock Stage 1.
    if os.environ.get("EVIE_TEST_DOCKER") != "1":
        monkeypatch.setattr(hooks_capsule, "image_preflight",
                            lambda: "sha256:" + "a"*64)
        def simulated_docker(title, script, seconds, *, image_id):
            assert image_id == "sha256:" + "a"*64
            return legacy_hooks.subprocess_run(title, script, seconds)
        monkeypatch.setattr(hooks_capsule, "run_hooks_isolated", simulated_docker)
    script = tmp_path / "script.txt"
    script.write_text(SCRIPT, encoding="utf-8")
    folder = tmp_path / "session"
    report = flow.start_session(
        session_dir=str(folder), script_file=str(script),
        topic="EVIE Creator Loop", confirm=True,
    )
    assert report["state"] == flow.STATES[0]
    return folder, report, script


def signed_lease(tmp_path, started, *, wrong_stage=False):
    folder, paused, _ = started
    private, public = tmp_path / "lease-private.pem", tmp_path / "trusted.pem"
    create_keypair(str(private), str(public), PASSWORD)
    key = load_private_key(private, PASSWORD)
    lease = issue_local_lease(
        artifact_sha=paused["hooksArtifactSha256"],
        source_sha=distribution._source_check()[1],
        stage_dir=str(folder / ("other" if wrong_stage else "distribution")),
        private_key=key,
    )
    lease_path = tmp_path / "signed.lease.json"
    lease_path.write_text(json.dumps(lease), encoding="utf-8")
    return dict(
        session_dir=str(folder), lease_file=str(lease_path),
        trusted_public=str(public), ledger=str(tmp_path / "nonce-ledger.sqlite"),
        confirm=True,
    )


def mock_isolated_backend(monkeypatch):
    monkeypatch.setattr(capsule, "image_preflight", lambda: "sha256:" + "a"*64)
    monkeypatch.setattr(isolated, "image_preflight", lambda: "sha256:" + "a"*64)
    real_worker = distribution._run_second_step
    def fake_docker(topic, hooks, seconds, *, image_id):
        # The normal suite exercises real distribution production but this is
        # NOT Docker. Only the dedicated CI lane proves real isolation.
        assert image_id == "sha256:" + "a"*64
        return real_worker(topic, hooks, seconds)
    monkeypatch.setattr(isolated, "run_isolated", fake_docker)


def test_start_persists_real_hooks_and_pauses_without_authorizing_stage_two(started):
    folder, first, _ = started
    assert first["stageOneExecutedLocally"] is True
    assert first["stageOneOSIsolated"] is True
    assert first["stageOneIsolation"]["profile"] == hooks_capsule.PROFILE
    assert first["stageOneIsolation"]["networkMode"] == "none"
    assert first["stageTwoExecuted"] is False
    assert first["signedApprovalReceived"] is False
    assert first["externalPublishingAuthorized"] is False
    assert sorted(path.name for path in folder.iterdir()) == [
        flow.EVENT_1, "hooks",
    ]
    raw = (folder/"hooks"/"nine-hooks.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == first["hooksArtifactSha256"]
    status = flow.session_status(str(folder))
    assert status["state"] == flow.STATES[0]
    assert status["mayAutomaticallyResume"] is False
    assert status["publishingAuthorized"] is False
    assert flow.plan()["state"] == "plan_only"


def test_real_two_step_flow_with_mocked_container_keeps_every_boundary(tmp_path, started, monkeypatch):
    mock_isolated_backend(monkeypatch)
    kwargs = signed_lease(tmp_path, started)
    state = flow.resume_session(**kwargs)
    folder, paused, _ = started
    assert state["state"] == flow.STATES[2]
    assert state["approvedHooksSha256"] == paused["hooksArtifactSha256"]
    assert state["dockerProfile"] == capsule.PROFILE
    assert state["signedLeaseVerifiedByRunner"] is True
    assert state["externalPublishingAuthorized"] is False
    assert state["finalDone"] is False
    progress = flow.session_status(str(folder))
    assert progress["state"] == flow.STATES[2]
    source = json.loads((folder/"hooks"/"nine-hooks.json").read_text())
    draft = json.loads((folder/"distribution"/"distribution-draft.json").read_text())
    assert draft["hooks_used"] == source["hooks"][:5]
    assert (folder/flow.EVENT_1).exists()
    assert (folder/flow.EVENT_2).exists()
    assert (folder/flow.EVENT_3).exists()
    assert len(list((folder/"distribution").iterdir())) == 4
    with pytest.raises(ValueError, match="already attempted"):
        flow.resume_session(**kwargs)


def test_missing_docker_blocks_stage_one_before_creating_session(tmp_path, monkeypatch):
    monkeypatch.setattr(hooks_capsule, "image_preflight",
                        lambda: (_ for _ in ()).throw(ValueError("Docker absent")))
    script = tmp_path / "input.txt"
    script.write_text(SCRIPT, encoding="utf-8")
    session = tmp_path / "not-created"
    with pytest.raises(ValueError, match="Docker absent"):
        flow.start_session(session_dir=str(session), script_file=str(script),
                           topic="EVIE Creator Loop", confirm=True)
    assert not session.exists()


def test_old_host_started_session_may_be_inspected_but_not_resumed(tmp_path, started, monkeypatch):
    folder, record, _ = started
    event = folder / flow.EVENT_1
    old = json.loads(event.read_text())
    old["stageOneOSIsolated"] = False
    old.pop("stageOneIsolation", None)
    event.write_text(json.dumps(old))
    assert flow.session_status(str(folder))["stageOneIsolation"]["profile"] == "legacy-host-subprocess"
    kwargs = signed_lease(tmp_path, started)
    with pytest.raises(ValueError, match="Stage 1 requires"):
        flow.resume_session(**kwargs)
    assert not (folder/flow.EVENT_2).exists()


def test_missing_docker_fails_before_attempt_event_or_nonce_spend(tmp_path, started, monkeypatch):
    kwargs = signed_lease(tmp_path, started)
    monkeypatch.setattr(capsule, "image_preflight",
                        lambda: (_ for _ in ()).throw(ValueError("Docker not installed")))
    with pytest.raises(ValueError, match="Docker not installed"):
        flow.resume_session(**kwargs)
    folder = Path(kwargs["session_dir"])
    assert not (folder/flow.EVENT_2).exists()
    assert not (folder/"distribution").exists()
    assert not Path(kwargs["ledger"]).exists()
    assert flow.session_status(str(folder))["state"] == flow.STATES[0]


def test_wrong_signed_destination_denied_without_mutating_session(tmp_path, started, monkeypatch):
    mock_isolated_backend(monkeypatch)
    kwargs = signed_lease(tmp_path, started, wrong_stage=True)
    with pytest.raises(ValueError, match="artifact, source or destination"):
        flow.resume_session(**kwargs)
    assert flow.session_status(kwargs["session_dir"])["state"] == flow.STATES[0]
    assert not Path(kwargs["ledger"]).exists()


def test_resume_requires_separate_explicit_confirmation(tmp_path, started):
    kwargs = signed_lease(tmp_path, started)
    kwargs["confirm"] = False
    with pytest.raises(ValueError, match="human confirmation"):
        flow.resume_session(**kwargs)
    assert flow.session_status(kwargs["session_dir"])["state"] == flow.STATES[0]


def test_crashed_second_stage_is_not_restarted(tmp_path, started, monkeypatch):
    mock_isolated_backend(monkeypatch)
    kwargs = signed_lease(tmp_path, started)
    calls = []
    def fails(**args):
        calls.append(args)
        raise ValueError("first second-stage attempt failed")
    monkeypatch.setattr(isolated, "run_isolated_with_lease", fails)
    with pytest.raises(ValueError, match="attempt failed"):
        flow.resume_session(**kwargs)
    status = flow.session_status(kwargs["session_dir"])
    assert status["state"] == flow.STATES[1]
    assert status["stageTwoOutput"] is None
    with pytest.raises(ValueError, match="already attempted"):
        flow.resume_session(**kwargs)
    assert len(calls) == 1


def test_tampered_hooks_and_source_pointers_denied(tmp_path, started, monkeypatch):
    kwargs = signed_lease(tmp_path, started)
    folder, _, _ = started
    blob = folder/"hooks"/"nine-hooks.json"
    original = blob.read_bytes()
    blob.write_bytes(original+b" ")
    with pytest.raises(ValueError, match="SHA-256"):
        flow.resume_session(**kwargs)
    assert not (folder/flow.EVENT_2).exists()
    blob.write_bytes(original)
    event = folder/flow.EVENT_1
    changed = json.loads(event.read_text())
    changed["workflowSourceSha256"] = "a" * 64
    event.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="source revision changed"):
        flow.session_status(str(folder))


def test_existing_session_path_cannot_be_overwritten(tmp_path, started):
    folder, _, script = started
    original = (folder/flow.EVENT_1).read_bytes()
    with pytest.raises(ValueError, match="exists"):
        flow.start_session(
            session_dir=str(folder), script_file=str(script),
            topic="EVIE Creator Loop", confirm=True,
        )
    assert (folder/flow.EVENT_1).read_bytes() == original


@pytest.mark.skipif(os.environ.get("EVIE_TEST_DOCKER") != "1",
                    reason="Only explicit GitHub real Docker gate executes isolated flow")
def test_real_docker_two_stage_controller_and_no_external_publish(tmp_path, started):
    kwargs = signed_lease(tmp_path, started)
    outcome = flow.resume_session(**kwargs)
    assert outcome["state"] == flow.STATES[2]
    assert outcome["dockerProfile"] == capsule.PROFILE
    initial = json.loads((Path(kwargs["session_dir"])/flow.EVENT_1).read_text())
    assert initial["stageOneOSIsolated"] is True
    assert initial["stageOneIsolation"]["profile"] == hooks_capsule.PROFILE
    assert initial["stageOneIsolation"]["networkMode"] == "none"
    folder = Path(kwargs["session_dir"])
    assert flow.session_status(str(folder))["state"] == flow.STATES[2]
    capsule_receipt = json.loads(
        (folder/"distribution"/"lease-consumption.json").read_text())
    assert capsule_receipt["containerIsolation"]["networkMode"] == "none"
    assert capsule_receipt["publishingAuthorized"] is False
    assert capsule_receipt["signedExecutionReceipt"] is False
    assert not (folder/"distribution"/"published.json").exists()
    audit = completion_audit.audit_session(
        str(folder), lease_file=kwargs["lease_file"],
        trusted_public=kwargs["trusted_public"], ledger=kwargs["ledger"],
    )
    assert audit["completionContract"]["status"] == "LOCAL_DRAFT_CONTRACT_VERIFIED"
    assert audit["completionContract"]["fullyVerified"] is True
    assert audit["policy"]["finalProductDone"] is False
