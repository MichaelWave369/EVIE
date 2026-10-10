"""R15: R14 hooks → real v2 DistributionGenerator, separated by SHA confirmation."""
from __future__ import annotations
import hashlib,json,subprocess
import pytest
from tools import evie_supervised_hooks as first
from tools import evie_supervised_distribution as second

SCRIPT=("EVIE's local creator loop takes existing script notes and turns them "
        "into reviewable hooks. Every stage is local and still requires human "
        "editorial verification before any publication.\n")

@pytest.fixture()
def stage_one(tmp_path):
    source=tmp_path/"original-script.txt"
    source.write_text(SCRIPT,encoding="utf8")
    out=tmp_path/"hooks"
    report=first.stage_hooks(script_file=str(source),topic="EVIE Creator Loop",
                             stage_dir=str(out),confirm=True)
    return out,report

def test_actual_second_generator_consumes_reviewed_hooks(stage_one,tmp_path):
    hooks_dir,r14=stage_one
    dest=tmp_path/"distribution"
    out=second.stage_distribution(hooks_dir=str(hooks_dir),
        approved_hooks_sha256=r14["artifactSha256"],stage_dir=str(dest),confirm=True)
    assert out["schemaVersion"]=="evie.supervised-distribution-review/1"
    assert out["governance"]["operatorConfirmedExactDigest"] is True
    for key in ("operatorIdentityVerified","humanSignatureVerified","legacyRunnerInvoked",
                "databaseTouched","llmCalled","providerCredentialsProvided","externalPublishing",
                "networkSandboxEnforced","furtherExecutionAuthorized","editorialApprovalGranted","signed"):
        assert out["governance"][key] is False
    first_hooks=json.loads((hooks_dir/"nine-hooks.json").read_text())
    generated=(dest/"distribution-draft.json").read_bytes()
    body=json.loads(generated)
    assert body["hooks_used"]==first_hooks["hooks"][:5]
    assert body["tiktok_hooks"]==first_hooks["hooks"][:5]
    assert hashlib.sha256(generated).hexdigest()==out["distributionSha256"]
    assert out["approvedInputSha256"]==r14["artifactSha256"]
    assert len(list(dest.iterdir()))==3
    assert json.loads((dest/"distribution-review-receipt.json").read_text())==out
    assert json.loads((dest/"workflow-preflight.json").read_text())["executed"] is False

def test_wrong_digest_and_missing_confirmation_denied(stage_one,tmp_path):
    folder,receipt=stage_one
    for options in (
      {"confirm":False},{"approved_hooks_sha256":"f"*64},
      {"approved_hooks_sha256":"Not a SHA-256"},{"timeout":900},
    ):
        params={"hooks_dir":str(folder),"approved_hooks_sha256":receipt["artifactSha256"],
                "stage_dir":str(tmp_path/"blocked"),"confirm":True}
        params.update(options)
        with pytest.raises(ValueError):
            second.stage_distribution(**params)
    assert not (tmp_path/"blocked").exists()

def test_reject_tampered_input_and_claimed_authority(stage_one,tmp_path):
    folder,receipt=stage_one
    original=(folder/"nine-hooks.json").read_bytes()
    (folder/"nine-hooks.json").write_bytes(original+b" ")
    with pytest.raises(ValueError,match="SHA-256"):
        second.stage_distribution(hooks_dir=str(folder),approved_hooks_sha256=receipt["artifactSha256"],
                                  stage_dir=str(tmp_path/"blocked"),confirm=True)
    (folder/"nine-hooks.json").write_bytes(original)
    name=folder/"review-receipt.json"
    original_receipt=name.read_bytes()
    changed=json.loads(original_receipt)
    changed["governance"]["externalPublishing"]=True
    name.write_text(json.dumps(changed))
    with pytest.raises(ValueError,match="unsupported authority"):
        second.stage_distribution(hooks_dir=str(folder),approved_hooks_sha256=receipt["artifactSha256"],
                                  stage_dir=str(tmp_path/"blocked"),confirm=True)
    name.write_bytes(original_receipt)
    assert not (tmp_path/"blocked").exists()

def test_existing_destination_is_never_overwritten(stage_one,tmp_path):
    folder,receipt=stage_one
    dest=tmp_path/"existing"
    dest.mkdir()
    (dest/"saved.txt").write_text("DO NOT TOUCH")
    with pytest.raises(ValueError,match="exists"):
        second.stage_distribution(hooks_dir=str(folder),approved_hooks_sha256=receipt["artifactSha256"],
                                  stage_dir=str(dest),confirm=True)
    assert (dest/"saved.txt").read_text()=="DO NOT TOUCH"

def test_second_stage_rejects_fake_output_before_stage(stage_one,tmp_path,monkeypatch):
    folder,receipt=stage_one
    monkeypatch.setattr(second,"_run_second_step",lambda *args:{
        "schemaVersion":"evie.distribution-worker/1","module":"distribution_generator",
        "hooksConsumed":5,"artifactBase64":"e30=",
        "sha256":"a"*64,"inputHooksSha256":"b"*64})
    with pytest.raises(ValueError,match="digest mismatch"):
        second.stage_distribution(hooks_dir=str(folder),approved_hooks_sha256=receipt["artifactSha256"],
                                  stage_dir=str(tmp_path/"blocked"),confirm=True)
    assert not (tmp_path/"blocked").exists()

def test_subprocess_restricts_credentials_and_max_timeout(stage_one,tmp_path,monkeypatch):
    folder,receipt=stage_one
    monkeypatch.setenv("OPENAI_API_KEY","never-forward")
    def fake_run(command,**kw):
        assert "OPENAI_API_KEY" not in kw["env"]
        assert kw["stderr"]==subprocess.DEVNULL
        assert kw["timeout"]==20
        raise subprocess.TimeoutExpired(command,kw["timeout"])
    monkeypatch.setattr(second.subprocess,"run",fake_run)
    with pytest.raises(subprocess.TimeoutExpired):
        second.stage_distribution(hooks_dir=str(folder),approved_hooks_sha256=receipt["artifactSha256"],
                                  stage_dir=str(tmp_path/"blocked"),confirm=True)
    assert not (tmp_path/"blocked").exists()
