"""R23: real fail-closed execution readiness, not fake permission signals."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools import evie_execution_security as security
from tools import evie_safe
from tools import evie_local_service


def test_readiness_is_explicitly_closed_even_when_sources_are_healthy():
    report=security.assess()
    assert report["schemaVersion"]=="evie.execution-security-contract/1"
    assert report["status"]=="EXECUTION_GATE_CLOSED"
    assert report["promotionReady"] is False
    assert report["executionAllowed"] is False
    assert report["boundaries"]["httpExecutionRoutesEnabled"] is False
    assert report["boundaries"]["callerOsIdentityAuthenticated"] is False
    assert report["boundaries"]["directLegacyCliPathsStillExist"] is True
    assert report["boundaries"]["localSqliteIsTamperProof"] is False
    assert report["boundaries"]["signedApprovalCanBeIssuedByHttp"] is False
    assert report["boundaries"]["httpCanConsumeLease"] is False
    assert report["noWorkerExecuted"] is True
    assert report["noFilesWritten"] is True
    names={r["requirement"] for r in report["promotionRequirements"]}
    assert names==set(security.REQUIRED_FOR_PROMOTION)
    assert len(names)==6
    assert all(r["satisfied"] is False for r in report["promotionRequirements"])


def test_source_provenance_matches_real_repository_bytes():
    report=security.assess()
    assert set(report["sourceSha256"])==set(security.CONTRACT_SOURCES)
    for path,digest in report["sourceSha256"].items():
        assert hashlib.sha256((security.ROOT/path).read_bytes()).hexdigest()==digest


@pytest.mark.parametrize("candidate",[
    None,
    {"action":"start","verifiedPrincipal":True},
    {"action":"resume","operatorAuthenticated":True,"signedLeaseValid":True},
    {"action":"publish","signed":True,"role":"admin"},
    {"action":"dispatch","module":"subprocess","allChecksPassed":True},
    {"action":"execute","osIdentityVerified":True,
     "protectedLedger":True,"independentlyAttested":True},
    {"role":"root","capabilities":["*"],"securityMode":"disabled"},
    "token&cookie&approve&execute",
])
def test_forged_authority_and_caller_supplied_properties_never_grant_execution(candidate):
    rejected=security.deny_http_execution(intent=candidate)
    assert rejected["status"]=="DENIED"
    assert rejected["executionAllowed"] is False
    assert rejected["approvalConsumed"] is False
    assert rejected["workerStarted"] is False
    assert rejected["publishingAuthorized"] is False
    assert "token" not in str(rejected)


def test_http_service_serves_exact_current_read_only_contract():
    info=evie_local_service._data("/v1/security")
    assert info["mode"]=="read_only_security_contract"
    assert info["httpExecutionEndpointsEnabled"] is False
    assert info["publishingAuthorized"] is False
    assert info["data"]["executionAllowed"] is False
    assert "/v1/security" in evie_local_service.ROUTES
    assert "start" not in evie_local_service.ROUTES
    assert "resume" not in evie_local_service.ROUTES


def test_contract_refuses_missing_or_symlinked_source(monkeypatch,tmp_path):
    name="tools/evie_local_service.py"
    patched_root=tmp_path/"untrusted"
    patched_root.mkdir()
    monkeypatch.setattr(security,"ROOT",patched_root)
    with pytest.raises(ValueError,match="missing or untrusted"):
        security.assess()
    (patched_root/"tools").mkdir()
    other=tmp_path/"safe"
    other.write_text("code")
    (patched_root/name).symlink_to(other)
    with pytest.raises(ValueError,match="missing or untrusted"):
        security.assess()


def test_cli_is_read_only_and_never_has_promotion_or_execute_flag(capsys):
    assert security.main(["assess"])==0
    output=json.loads(capsys.readouterr().out)
    assert output["promotionReady"] is False
    assert output["executionAllowed"] is False
    with pytest.raises(SystemExit):
        security.main(["enable-execution"])
    with pytest.raises(SystemExit):
        security.main(["assess","--force","--allow-root"])


def test_legacy_exposure_remains_acknowledged_not_revoked():
    defaults=evie_safe.policy_report()
    assert defaults["legacyCommandsRemoved"] is False
    assert defaults["repositoryWideHostExecutionPrevented"] is False
    assert security.assess()["boundaries"]["directLegacyCliPathsStillExist"] is True
