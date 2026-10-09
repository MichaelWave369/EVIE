"""Security regression and real local offline revival smoke."""
import json
import pytest
from fastapi import HTTPException
from app.security.auth import api_key_is_configured, require_api_key
from app.settings import settings
from tools.evie_doctor import inspect, smoke_cad, check_workflow_references

@pytest.mark.parametrize("value", [None, "", "change-me", "change-me-long-random",
                                   "my-secret-key-change-this", "replace-with-a-unique-random-secret"])
def test_rejects_insecure_example_credentials(value):
    assert not api_key_is_configured(value)

def test_authentication_gate_is_fail_closed(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "")
    with pytest.raises(HTTPException) as error:
        require_api_key(x_api_key=None)
    assert error.value.status_code == 503
    monkeypatch.setattr(settings, "api_key", "change-me")
    with pytest.raises(HTTPException) as error:
        require_api_key(x_api_key="change-me")
    assert error.value.status_code == 503
    monkeypatch.setattr(settings, "api_key", "locally-generated-secret-for-tests-123")
    with pytest.raises(HTTPException) as error:
        require_api_key(x_api_key="incorrect")
    assert error.value.status_code == 401
    assert require_api_key(x_api_key="locally-generated-secret-for-tests-123") is None

def test_checks_broken_module_and_nested_workflow_links():
    flows = {"one": {"steps": [{"module": "known"}, {"workflow": "missing"}]},
             "two": {"steps": [{"module": "unknown"}]}}
    errors = check_workflow_references(flows, {"known"})
    assert len(errors) == 2

def test_doctor_never_exposes_key(monkeypatch):
    key = "do-not-print-this-secret-in-doctor-reports"
    monkeypatch.setattr(settings, "api_key", key)
    report = inspect()
    assert report["modules"]["registered_count"] >= 100
    assert report["workflows"]["configured_count"] >= 10
    assert key not in json.dumps(report)
    assert report["cad_smoke"]["status"] == "not_run"

def test_real_deterministic_cad_smoke_is_disposable():
    report = smoke_cad()
    assert report["status"] == "pass"
    assert report["walls"] == 5
    assert report["digest_verified"] is True
    assert report["persistent_artifacts"] is False
