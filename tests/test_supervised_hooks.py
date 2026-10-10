"""R14: local real HooksGenerator, manually staged and fail-closed."""
import hashlib, json, subprocess
import pytest
from tools import evie_supervised_hooks as hooks

SCRIPT = ("The public EVIE dashboard maps source capabilities and keeps downstream "
          "execution behind review. A test receipt does not prove that a recipient "
          "accepted an artifact. Start with a bounded plan, inspect the evidence, "
          "and decide what to approve separately.\n")

def script(tmp_path):
    file=tmp_path/"input.txt"
    file.write_text(SCRIPT,encoding="utf-8")
    return file

def test_real_original_hooks_generator_run(tmp_path,monkeypatch):
    monkeypatch.setenv("EV_OPENAI_API_KEY","never-export-this-secret")
    origin=script(tmp_path)
    stage=tmp_path/"review-001"
    record=hooks.stage_hooks(script_file=str(origin),topic="EVIE Creator Loop",
                             stage_dir=str(stage),confirm=True)
    assert record["status"]=="staged_for_human_review"
    assert record["hookCount"]==9 and record["categoryCount"]==3
    assert sorted(f.name for f in stage.iterdir())==[
      "nine-hooks-review.md","nine-hooks.json","review-receipt.json","workflow-preflight.json"]
    blob=(stage/"nine-hooks.json").read_bytes()
    artifact=json.loads(blob)
    assert hashlib.sha256(blob).hexdigest()==record["artifactSha256"]
    assert len(artifact["hooks"])==9
    assert artifact["categories"]["educational"]==artifact["hooks"][:3]
    assert artifact["categories"]["controversial"]==artifact["hooks"][3:6]
    assert artifact["categories"]["curiosity"]==artifact["hooks"][6:9]
    assert artifact["topic"]=="EVIE Creator Loop"
    assert json.loads((stage/"review-receipt.json").read_text())==record
    plan=json.loads((stage/"workflow-preflight.json").read_text())
    assert plan["sourceSha256"]==record["workflowSourceSha256"]
    assert plan["executed"] is False
    assert record["governance"]["localModuleExecuted"] is True
    for key in ("legacyRunnerInvoked","databaseTouched","llmCalled","providerCredentialsProvided",
                "externalPublishing","networkSandboxEnforced","authorizedForFutureRuns","signed"):
        assert record["governance"][key] is False
    assert "never-export-this-secret" not in json.dumps(record)
    assert "never-export-this-secret" not in (stage/"nine-hooks-review.md").read_text()

def test_confirm_and_allowlist_denial_before_writes(tmp_path):
    origin=script(tmp_path)
    for options in (
        {"confirm":False},
        {"confirm":True,"workflow":"youtube_flywheel"},
        {"confirm":True,"timeout":999},
        {"confirm":True,"topic":"input; echo secrets"},
    ):
        args={"script_file":str(origin),"topic":"EVIE Creator Loop",
              "stage_dir":str(tmp_path/"never-written"),"confirm":True}
        args.update(options)
        with pytest.raises(ValueError):
            hooks.stage_hooks(**args)
    assert not (tmp_path/"never-written").exists()

def test_oversize_short_and_symlink_scripts_denied(tmp_path):
    root=tmp_path/"script.txt"
    root.write_text("short",encoding="utf8")
    with pytest.raises(ValueError): hooks.read_input(root)
    root.write_text("a"*8193,encoding="utf8")
    with pytest.raises(ValueError): hooks.read_input(root)
    root.write_text(SCRIPT,encoding="utf8")
    link=tmp_path/"alias.txt"
    link.symlink_to(root)
    with pytest.raises(ValueError): hooks.read_input(link)

def test_existing_stage_folder_never_overwritten(tmp_path):
    input_path=script(tmp_path)
    stage=tmp_path/"existing"
    stage.mkdir()
    (stage/"sentinel").write_text("keep this")
    with pytest.raises(ValueError):
        hooks.stage_hooks(script_file=str(input_path),topic="EVIE Creator Loop",
                          stage_dir=str(stage),confirm=True)
    assert (stage/"sentinel").read_text()=="keep this"

def test_tampered_child_output_rejected(tmp_path,monkeypatch):
    origin=script(tmp_path)
    monkeypatch.setattr(hooks,"subprocess_run",lambda *args: {
        "schemaVersion":"evie.supervised-hooks-worker/1",
        "workflow":hooks.WORKFLOW,"module":hooks.MODULE,
        "topic":"EVIE Creator Loop","hooks":9,"categories":3,
        "artifactBase64":"e30=","sha256":"a"*64,"scriptSha256":"b"*64,
    })
    stage=tmp_path/"declined"
    with pytest.raises(ValueError,match="digest"):
        hooks.stage_hooks(script_file=str(origin),topic="EVIE Creator Loop",
                          stage_dir=str(stage),confirm=True)
    assert not stage.exists()

def test_changes_to_audited_workflow_declined(tmp_path,monkeypatch):
    origin=script(tmp_path)
    original=hooks.read_source
    def modified():
        registry,names,digest=original()
        registry[hooks.WORKFLOW]["steps"].append({"module":"youtube_publisher"})
        return registry,names,digest
    monkeypatch.setattr(hooks,"read_source",modified)
    with pytest.raises(ValueError,match="workflow"):
        hooks.stage_hooks(script_file=str(origin),topic="EVIE Creator Loop",
                          stage_dir=str(tmp_path/"nope"),confirm=True)
    assert not (tmp_path/"nope").exists()

def test_provider_environment_not_forwarded(tmp_path,monkeypatch):
    origin=script(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY","never-forward")
    def reject(command,**kwargs):
        assert "OPENAI_API_KEY" not in kwargs["env"]
        assert kwargs["stderr"]==subprocess.DEVNULL
        assert kwargs["timeout"]==20
        assert kwargs["input"] and b"EVIE Creator Loop" in kwargs["input"]
        raise subprocess.TimeoutExpired(command,kwargs["timeout"])
    monkeypatch.setattr(hooks.subprocess,"run",reject)
    with pytest.raises(subprocess.TimeoutExpired):
        hooks.stage_hooks(script_file=str(origin),topic="EVIE Creator Loop",
                          stage_dir=str(tmp_path/"timeout"),confirm=True)
    assert not (tmp_path/"timeout").exists()
