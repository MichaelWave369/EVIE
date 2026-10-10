"""R21: default safe front door; original real generators, no legacy dispatch.

Normal suite mocks Docker only while calling ORIGINAL deterministic EVIE modules.
Only EVIE_TEST_DOCKER=1 in the dedicated workflow executes true Docker.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path

import pytest

from tools import evie_safe as safe
from tools import evie_governed_flow as flow
from tools import evie_completion_audit as audit
from tools import evie_hooks_container as hooks_capsule
from tools import evie_container_runner as capsule
from tools import evie_isolated_distribution as isolated
from tools import evie_supervised_hooks as hooks
from tools import evie_supervised_distribution as distribution
from tools.evie_attest import create_keypair, load_private_key
from tools.evie_action_lease_contract import issue_local_lease

SCRIPT=("A locally stored manuscript provides bounded ideas and factual context. "
        "EVIE generates editable hooks, then pauses for human review, and "
        "only a separately signed offline action may produce downstream drafts.\n")
PHRASE="test-local-key-long-safe-default-passphrase"


@pytest.fixture()
def real_fixture(tmp_path,monkeypatch):
    if os.environ.get("EVIE_TEST_DOCKER")!="1":
        monkeypatch.setattr(hooks_capsule,"image_preflight",lambda:"sha256:"+"a"*64)
        monkeypatch.setattr(hooks_capsule,"run_hooks_isolated",
                            lambda title,script,seconds,*,image_id:
                            hooks.subprocess_run(title,script,seconds))
        monkeypatch.setattr(capsule,"image_preflight",lambda:"sha256:"+"b"*64)
        monkeypatch.setattr(isolated,"image_preflight",lambda:"sha256:"+"b"*64)
        monkeypatch.setattr(isolated,"run_isolated",
                            lambda title,lines,seconds,*,image_id:
                            distribution._run_second_step(title,lines,seconds))
    script=tmp_path/"draft.txt"
    script.write_text(SCRIPT,encoding="utf-8")
    return tmp_path,script


def parsed(*words):
    return safe.parser().parse_args(list(words))


def test_policy_is_read_only_and_admits_legacy_bypasses():
    policy=safe.dispatch(parsed("policy"))
    assert policy["schemaVersion"]==safe.SCHEMA
    assert policy["recommendedCommand"]=="python -m tools.evie_safe"
    assert policy["noWorkerExecuted"] is True
    assert policy["legacyCommandsRemoved"] is False
    assert policy["repositoryWideHostExecutionPrevented"] is False
    assert policy["networkOrHostIsolationProvenByThisReport"] is False
    assert policy["publishingAuthorized"] is False
    assert policy["allowedActions"]==["policy","entrypoints","plan","start","status","resume","audit"]
    lanes={x["id"]:x for x in policy["legacyRoutes"]}
    assert len(lanes)==6
    for key in safe.LEGACY_ENTRYPOINT_IDS:
        assert lanes[key]["migrationDisposition"]==safe.LEGACY_STATUS
        assert lanes[key]["hostExecutionPossible"] is True
    assert lanes["preferred_dual_capsule_controller"]["dockerRequiredByThisCommand"] is True


def test_read_only_commands_return_no_exec_claims():
    plan=safe.dispatch(parsed("plan"))
    assert plan["data"]["state"]=="plan_only"
    assert plan["data"]["nextStageExecuted"] is False
    assert plan["publishingAuthorized"] is False
    inv=safe.dispatch(parsed("entrypoints"))
    assert inv["data"]["hostRuntimeProbed"] is False
    assert inv["data"]["writesPerformed"] is False


def test_unsupported_actions_and_dynamic_worker_flags_are_refused():
    for argv in [
        ["legacy_host_hooks"],["publish"],["run","hooks_generator"],
        ["start","--module","youtube_publisher"],["start","--worker","shell"],
        ["resume","--shell","curl"],["entrypoints","--run"],
    ]:
        with pytest.raises(SystemExit):
            safe.parser().parse_args(argv)
    with pytest.raises(ValueError,match="not allowlisted"):
        safe.dispatch(type("Unsafe",(),{"command":"publish"})())


def test_no_confirmation_rejects_before_sandbox_invocation(real_fixture,monkeypatch):
    tmp,script=real_fixture
    monkeypatch.setattr(flow,"start_session",lambda **kw:
        (_ for _ in ()).throw(AssertionError("should not run")))
    args=parsed("start","--session-dir",str(tmp/"no-session"),
      "--script-file",str(script),"--topic","EVIE Creator Loop")
    with pytest.raises(ValueError,match="explicit confirmation"):
        safe.dispatch(args)
    assert not (tmp/"no-session").exists()


def test_safe_start_uses_real_original_hooks_and_pauses(real_fixture):
    tmp,script=real_fixture
    session=tmp/"session"
    out=safe.dispatch(parsed("start","--session-dir",str(session),
       "--script-file",str(script),"--topic","EVIE Creator Loop",
       "--confirm-local-execution"))
    assert out["mode"]=="governed_hooks_paused"
    assert out["data"]["state"]=="paused_for_human_review"
    assert out["data"]["stageOneOSIsolated"] is True
    assert out["data"]["stageTwoExecuted"] is False
    hooks_json=json.loads((session/"hooks"/"nine-hooks.json").read_text())
    assert len(hooks_json["hooks"])==9
    assert hashlib.sha256((session/"hooks"/"nine-hooks.json").read_bytes()).hexdigest()==out["data"]["hooksArtifactSha256"]
    assert not (session/"distribution").exists()
    status=safe.dispatch(parsed("status","--session-dir",str(session)))
    assert status["data"]["mayAutomaticallyResume"] is False
    assert status["data"]["state"]=="paused_for_human_review"
    result=safe.dispatch(parsed("audit","--session-dir",str(session)))
    assert result["data"]["completionContract"]["status"]=="WAITING_FOR_REVIEW"
    assert result["data"]["policy"]["finalProductDone"] is False


def test_safe_resume_requires_confirmation_even_with_valid_paths(monkeypatch):
    monkeypatch.setattr(flow,"resume_session",lambda **kw:
        (_ for _ in ()).throw(AssertionError("resume should not run")))
    args=parsed("resume","--session-dir","path",
        "--lease-file","sign.lease.json","--trusted-public","trust.pem",
        "--ledger","nonce.sqlite")
    with pytest.raises(ValueError,match="explicit confirmation"):
        safe.dispatch(args)


def test_audit_requires_all_independent_evidence_inputs(real_fixture):
    tmp,script=real_fixture
    session=tmp/"session"
    safe.dispatch(parsed("start","--session-dir",str(session),
       "--script-file",str(script),"--topic","EVIE Creator Loop",
       "--confirm-local-execution"))
    arg=parsed("audit","--session-dir",str(session),"--lease-file","thing.json")
    with pytest.raises(ValueError,match="all three"):
        safe.dispatch(arg)
    assert not (tmp/"nonce.sqlite").exists()


def test_actual_signed_two_stage_via_default_route_no_false_done(real_fixture):
    tmp,script=real_fixture
    session=tmp/"session"
    first=safe.dispatch(parsed("start","--session-dir",str(session),
       "--script-file",str(script),"--topic","EVIE Creator Loop",
       "--confirm-local-execution"))["data"]
    private,trusted=tmp/"signing.pem",tmp/"trusted.pem"
    create_keypair(str(private),str(trusted),PHRASE)
    key=load_private_key(private,PHRASE)
    lease=issue_local_lease(
        artifact_sha=first["hooksArtifactSha256"],
        source_sha=first["workflowSourceSha256"],
        stage_dir=str(session/"distribution"),private_key=key)
    lease_file=tmp/"signed.lease.json"
    lease_file.write_text(json.dumps(lease),encoding="utf-8")
    ledger=tmp/"nonce.sqlite"
    args=["resume","--session-dir",str(session),
          "--lease-file",str(lease_file),"--trusted-public",str(trusted),
          "--ledger",str(ledger),"--confirm-local-execution"]
    done=safe.dispatch(parsed(*args))
    assert done["mode"]=="governed_draft_staged"
    assert done["data"]["state"]=="distribution_staged_for_review"
    assert done["data"]["finalDone"] is False
    assert done["publishingAuthorized"] is False
    audit_args=["audit","--session-dir",str(session),"--lease-file",str(lease_file),
                "--trusted-public",str(trusted),"--ledger",str(ledger)]
    checked=safe.dispatch(parsed(*audit_args))
    assert checked["data"]["completionContract"]["status"]=="LOCAL_DRAFT_CONTRACT_VERIFIED"
    assert checked["data"]["policy"]["finalProductDone"] is False
    assert checked["data"]["policy"]["publishingAuthorized"] is False
    with pytest.raises(ValueError,match="already attempted"):
        safe.dispatch(parsed(*args))


def test_public_cli_emits_closed_status_not_debug_trace(capsys):
    value=safe.main(["plan"])
    assert value==0
    data=json.loads(capsys.readouterr().out)
    assert data["mode"]=="source_only_governed_plan"
    failed=safe.main(["status","--session-dir","./directory-not-present-r21"])
    assert failed==1
    data=json.loads(capsys.readouterr().out)
    assert data["legacyFallback"] is False
    assert data["publishingAuthorized"] is False
    assert data["finalDoneAuthorized"] is False
