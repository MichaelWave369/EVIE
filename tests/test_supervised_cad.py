"""R13: actual one-step CAD workflow executed locally, staged only for human review."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.family_gate.openblue_preflight import inspect_openblue_bytes
from tools import evie_supervised


def test_supervised_fixed_cad_workflow_stages_real_artifact(tmp_path, monkeypatch):
    monkeypatch.setenv("EV_OPENAI_API_KEY", "must-not-leak")
    monkeypatch.setenv("EV_GUMROAD_ACCESS_TOKEN", "must-not-leak")
    stage = tmp_path / "cad-review-001"
    result = evie_supervised.supervised_run(str(stage), confirm=True)
    assert stage.is_dir()
    assert sorted(p.name for p in stage.iterdir()) == [
        "openblueprint.evie-proposal.json", "review-receipt.json", "workflow-preflight.json",
    ]
    assert result["schemaVersion"] == "evie.supervised-cad-review/1"
    assert result["status"] == "staged_for_human_review"
    assert result["workflow"] == "openblueprint_concept_floor_plan"
    assert result["module"] == "openblueprint_floor_plan"
    assert result["scenario"] == "cad_supervised_24x16_v1"
    assert result["governance"]["localFixtureExecuted"] is True
    assert result["governance"]["legacyRunnerInvoked"] is False
    assert result["governance"]["databaseTouched"] is False
    assert result["governance"]["providerCredentialsProvided"] is False
    assert result["governance"]["networkSandboxEnforced"] is False
    assert result["governance"]["recipientAccepted"] is False
    assert result["governance"]["projectImported"] is False
    assert result["governance"]["downstreamActionAuthorized"] is False
    assert result["governance"]["signed"] is False
    data = (stage / "openblueprint.evie-proposal.json").read_bytes()
    assert hashlib.sha256(data).hexdigest() == result["artifactSha256"]
    assert inspect_openblue_bytes(data)["walls"] == 5
    assert inspect_openblue_bytes(data)["symbols"] == 2
    assert result["artifactBytes"] == len(data)
    assert json.loads((stage / "review-receipt.json").read_text()) == result
    plan = json.loads((stage / "workflow-preflight.json").read_text())
    assert plan["sourceSha256"] == result["workflowSourceSha256"]
    assert plan["executed"] is False  # R12 advisory plan, not runtime evidence
    assert plan["databaseTouched"] is False
    assert plan["executionAuthorized"] is False
    assert "must-not-leak" not in json.dumps(result)
    assert "EV_OPENAI_API_KEY" not in json.dumps(result)


def test_denies_unapproved_or_non_allowlisted_workflow_without_writing(tmp_path):
    for kwargs in (
        {"confirm": False},
        {"confirm": True, "workflow": "vault_to_money_publish"},
        {"confirm": True, "timeout": 500},
    ):
        with pytest.raises(ValueError):
            evie_supervised.supervised_run(str(tmp_path / "not-written"), **kwargs)
    assert list(tmp_path.iterdir()) == []


def test_does_not_overwrite_existing_stage(tmp_path):
    stage = tmp_path / "review"
    stage.mkdir()
    sentinel = stage / "existing.txt"
    sentinel.write_text("DO NOT TOUCH")
    with pytest.raises(ValueError, match="exists"):
        evie_supervised.supervised_run(str(stage), confirm=True)
    assert sentinel.read_text() == "DO NOT TOUCH"


def test_detects_changed_workflow_before_execution(monkeypatch, tmp_path):
    original = evie_supervised.read_source
    def compromised():
        workflows, modules, digest = original()
        workflows["openblueprint_concept_floor_plan"]["steps"].append({"module": "youtube_publisher"})
        return workflows, modules, digest
    monkeypatch.setattr(evie_supervised, "read_source", compromised)
    with pytest.raises(ValueError, match="steps changed"):
        evie_supervised.supervised_run(str(tmp_path / "blocked"), confirm=True)
    assert not (tmp_path / "blocked").exists()


def test_rejects_fake_worker_digest_and_shape_before_stage(monkeypatch, tmp_path):
    monkeypatch.setattr(evie_supervised, "_run_worker", lambda _: {
        "schemaVersion":"evie.supervised-worker-output/1",
        "workflow":"openblueprint_concept_floor_plan",
        "module":"openblueprint_floor_plan",
        "sha256":"a"*64,
        "artifactBase64":"e30=",
        "sourceRunId":"evie-cad-a",
        "walls":5,"symbols":2,"units":"ft",
    })
    with pytest.raises(ValueError, match="digest mismatch"):
        evie_supervised.supervised_run(str(tmp_path / "rejected"), confirm=True)
    assert not (tmp_path / "rejected").exists()


def test_do_not_stage_in_repository():
    with pytest.raises(ValueError, match="outside public EVIE"):
        evie_supervised._stage_directory(str(evie_supervised.ROOT / "unsafe-review"))


def test_worker_process_credential_allowlist(monkeypatch, tmp_path):
    import subprocess
    seen = {}
    def no_run(cmd, **kwargs):
        seen.update(kwargs)
        raise subprocess.TimeoutExpired(cmd, kwargs["timeout"])
    monkeypatch.setattr(evie_supervised.subprocess, "run", no_run)
    monkeypatch.setenv("EV_OPENAI_API_KEY", "this-is-secret")
    with pytest.raises(subprocess.TimeoutExpired):
        evie_supervised.supervised_run(str(tmp_path / "timeout"), confirm=True)
    assert not (tmp_path / "timeout").exists()
    assert "EV_OPENAI_API_KEY" not in seen["env"]
    assert seen["stderr"] == subprocess.DEVNULL
    assert seen["timeout"] == 20
