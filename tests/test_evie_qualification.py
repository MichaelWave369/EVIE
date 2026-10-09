"""R7: opt-in offline qualification receipts and strict allowlist tests."""
import json
import os
import pytest
from tools.evie_qualify import (
    RECEIPT_SCHEMA, SCENARIOS, EXPECTED_CHECKS, _checked_observation,
    available_scenarios, run_qualification, write_receipt_exclusive,
)

def test_only_audited_cad_scenario_is_allowlisted():
    assert list(SCENARIOS) == ["openblueprint_floor_plan"]
    assert available_scenarios()[0]["scenario"] == "cad_rectangular_concept_v1"
    with pytest.raises(ValueError, match="not allowlisted"):
        run_qualification("youtube_publisher")
    with pytest.raises(ValueError, match="Timeout"):
        run_qualification("openblueprint_floor_plan", timeout=0)

def test_actual_qualification_in_separate_process_has_verified_fixture(monkeypatch):
    monkeypatch.setenv("EV_OPENAI_API_KEY", "must-not-leak")
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-leak")
    monkeypatch.setenv("EV_GUMROAD_ACCESS_TOKEN", "must-not-leak")
    receipt = run_qualification("openblueprint_floor_plan")
    assert receipt["schemaVersion"] == RECEIPT_SCHEMA
    assert receipt["status"] == "pass"
    assert receipt["origin"] == "local-subprocess-observation"
    assert receipt["scenario"] == "cad_rectangular_concept_v1"
    assert set(receipt["checks"]) == EXPECTED_CHECKS
    assert all(value is True for value in receipt["checks"].values())
    assert receipt["effectPolicy"]["providerEnvironmentStripped"] is True
    assert receipt["effectPolicy"]["networkSandboxEnforced"] is False
    assert receipt["trust"]["signed"] is False
    assert receipt["observedWalls"] == 5
    assert "must-not-leak" not in json.dumps(receipt)
    assert "EV_OPENAI_API_KEY" not in json.dumps(receipt)
    assert len(receipt["artifactSha256"]) == 64

def test_fake_or_incomplete_worker_output_is_not_qualified():
    raw = {
        "schemaVersion": "evie.qualification-observation/1",
        "module": "openblueprint_floor_plan",
        "scenario": "cad_rectangular_concept_v1", "status": "pass",
        "checks": {x: True for x in EXPECTED_CHECKS},
        "sourceSha256": "a" * 64, "artifactSha256": "b" * 64,
        "observedWalls": 5, "observedSymbols": 2,
    }
    assert _checked_observation(raw, "openblueprint_floor_plan", "a" * 64)["observedWalls"] == 5
    with pytest.raises(ValueError):
        _checked_observation({**raw, "checks": {**raw["checks"], "digest_match": False}},
                             "openblueprint_floor_plan", "a" * 64)
    with pytest.raises(ValueError):
        _checked_observation(raw, "openblueprint_floor_plan", "c" * 64)
    with pytest.raises(ValueError):
        _checked_observation({**raw, "observedWalls": 0}, "openblueprint_floor_plan", "a" * 64)

def test_local_receipt_write_requires_explicit_new_filename(tmp_path):
    target = tmp_path / "cad-qualification.json"
    payload = {"schemaVersion": RECEIPT_SCHEMA, "status": "pass", "fake": False}
    write_receipt_exclusive(str(target), payload)
    assert json.loads(target.read_text(encoding="utf-8")) == payload
    with pytest.raises(FileExistsError):
        write_receipt_exclusive(str(target), payload)
    with pytest.raises(ValueError):
        write_receipt_exclusive(str(tmp_path/"nonexistent"/"receipt.json"), payload)

def test_timeout_does_not_claim_pass(monkeypatch):
    import subprocess
    def fail_timeout(*args, **kwargs):
        assert kwargs["env"].get("EV_OPENAI_API_KEY") is None
        assert kwargs["env"].get("OPENAI_API_KEY") is None
        assert kwargs["cwd"] != str(os.getcwd())
        raise subprocess.TimeoutExpired("worker", kwargs["timeout"])
    monkeypatch.setenv("EV_OPENAI_API_KEY", "must-not-leak")
    monkeypatch.setattr("tools.evie_qualify.subprocess.run", fail_timeout)
    receipt = run_qualification("openblueprint_floor_plan", timeout=1)
    assert receipt["status"] == "fail"
    assert receipt["reason"] == "timeout"
    assert receipt["artifactSha256"] is None
