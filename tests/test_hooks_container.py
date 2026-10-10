"""R19 Stage 1 Docker hooks capsule: source isolation, denied fallback, real output."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest

from tools import evie_hooks_container as hooks
from tools import evie_container_runner as distribution_capsule
from tools import evie_governed_flow as flow

IMAGE = "sha256:" + "a"*64
SCRIPT = ("The verified content production flow generates hooks from a local script. "
          "No external publishing is allowed without a separate policy review. "
          "Every outbound action must remain explicitly denied.\n")


def test_capsule_excludes_registry_and_credentials(tmp_path):
    root = tmp_path / "hook-files"
    root.mkdir()
    hashes = hooks.stage_hooks_capsule(root)
    assert set(hashes) == set(hooks.HOOK_FILES)
    files = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    assert len(files) == 8
    assert "app/modules/__init__.py" in files
    assert (root/"app/modules/__init__.py").read_bytes() == b""
    assert "app/settings.py" not in files
    assert "configs/workflows.json" not in files
    assert ".env" not in files
    assert "app/modules_v2/distribution_generator.py" not in files
    for filename, digest in hashes.items():
        assert hashlib.sha256((root/filename).read_bytes()).hexdigest() == digest


def test_capsule_uses_same_offline_hardening_but_fixed_hooks_entry(tmp_path, monkeypatch):
    root = tmp_path / "hooks"
    root.mkdir()
    image_id = IMAGE
    original_run = distribution_capsule.docker_command(image_id, root)
    assert hooks.HOOK_ENTRY != original_run[-1]
    assert hooks.isolation_metadata(image_id)["networkMode"] == "none"
    assert hooks.isolation_metadata(image_id)["hostCheckoutMounted"] is False
    assert "--network=none" in original_run
    assert "--cap-drop=ALL" in original_run
    assert "--read-only" in original_run
    assert "--pull=never" in original_run
    assert "-i" in original_run
    assert "--user=65534:65534" in original_run


def test_stage_one_docker_child_does_not_forward_secrets(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-be-forwarded")
    monkeypatch.setenv("EV_GUMROAD_ACCESS_TOKEN", "must-not-be-forwarded")
    seen = {}
    def no_docker(argv, **kwargs):
        seen["argv"] = argv
        seen["env"] = kwargs["env"]
        seen["input"] = kwargs["input"]
        assert "OPENAI_API_KEY" not in kwargs["env"]
        assert "EV_GUMROAD_ACCESS_TOKEN" not in kwargs["env"]
        assert kwargs["stderr"] == subprocess.DEVNULL
        assert kwargs["timeout"] == 6
        assert argv[-1] == hooks.HOOK_ENTRY
        assert "--network=none" in argv
        raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
    monkeypatch.setattr(hooks.subprocess, "run", no_docker)
    with pytest.raises(ValueError, match="time budget"):
        hooks.run_hooks_isolated("EVIE Creator Loop", SCRIPT, 6, image_id=IMAGE)
    assert seen["input"] and b"EVIE Creator Loop" in seen["input"]


def test_invalid_input_or_image_does_not_invoke_docker(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("should not call Docker")
    monkeypatch.setattr(hooks.subprocess, "run", refuse)
    with pytest.raises(ValueError):
        hooks.run_hooks_isolated("EVIE Creator Loop", "short", 20, image_id=IMAGE)
    with pytest.raises(ValueError):
        hooks.run_hooks_isolated("EVIE Creator Loop", SCRIPT, 20, image_id="latest")
    with pytest.raises(ValueError):
        hooks.run_hooks_isolated("bad;command", SCRIPT, 20, image_id=IMAGE)


@pytest.mark.skipif(os.environ.get("EVIE_TEST_DOCKER") != "1",
                    reason="Real hooks Docker requires the explicit CI container lane")
def test_real_hooks_module_in_offline_docker():
    image_id = distribution_capsule.image_preflight()
    result = hooks.run_hooks_isolated("EVIE Creator Loop", SCRIPT, 20, image_id=image_id)
    assert result["schemaVersion"] == "evie.supervised-hooks-worker/1"
    assert result["workflow"] == "local_content_hooks_review"
    assert result["hooks"] == 9
    assert result["categories"] == 3
    assert result["scriptSha256"] == hashlib.sha256(SCRIPT.encode("utf-8")).hexdigest()
    assert result["sha256"] and len(result["sha256"]) == 64
