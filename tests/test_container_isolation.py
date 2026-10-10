"""R17: Docker policy, minimal source capsule and actual signed-lease handoff.

The normal suite exercises all fail-closed contracts with no Docker dependency.
The additional Docker CI workflow sets EVIE_TEST_DOCKER=1 and executes the actual
generator inside a network-disabled, read-only resource-bounded container.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tools.evie_attest import create_keypair, load_private_key
from tools import evie_supervised_hooks as first
from tools import evie_supervised_distribution as dist
from tools.evie_action_lease_contract import issue_local_lease
from tools.evie_container_runner import (
    SOURCE_CAPSULE, PROFILE, IMAGE, docker_command, image_preflight,
    isolation_metadata, run_isolated, stage_capsule,
)
from tools.evie_isolated_distribution import run_isolated_with_lease

SHA = "sha256:" + "a" * 64
SCRIPT = (
    "Create a supervised short content draft from actual EVIE modules. "
    "This is a local template and will not call any social publisher. "
    "Inspect each generated hook before using it elsewhere.\n"
)


@pytest.fixture
def approval(tmp_path):
    script = tmp_path / "input.txt"
    script.write_text(SCRIPT, encoding="utf8")
    folder = tmp_path / "stage1"
    prior = first.stage_hooks(
        script_file=str(script), topic="EVIE Creator Loop",
        stage_dir=str(folder), confirm=True,
    )
    destination = tmp_path / "stage2"
    private, public = tmp_path / "signing.pem", tmp_path / "trusted.pem"
    create_keypair(str(private), str(public), "long-local-private-passphrase")
    key = load_private_key(private, "long-local-private-passphrase")
    lease = issue_local_lease(
        artifact_sha=prior["artifactSha256"],
        source_sha=dist._source_check()[1],
        stage_dir=str(destination), private_key=key,
    )
    lease_path = tmp_path / "approved.lease.json"
    lease_path.write_text(json.dumps(lease), encoding="utf8")
    kwargs = dict(
        hooks_dir=str(folder), approved_hooks_sha256=prior["artifactSha256"],
        stage_dir=str(destination), lease_file=str(lease_path),
        trusted_public=str(public), ledger=str(tmp_path / "shared-lease-ledger.sqlite"),
        confirm=True,
    )
    return kwargs


def test_docker_args_are_fixed_nonprivileged_and_offline(tmp_path):
    folder = tmp_path / "capsule"
    folder.mkdir()
    argv = docker_command(SHA, folder)
    assert argv[:4] == ["docker", "run", "--rm", "--pull=never"]
    assert "-i" in argv and "-t" not in argv  # Pipe stdin only, never a TTY.
    for mandatory in (
        "--network=none", "--read-only", "--cap-drop=ALL",
        "--security-opt=no-new-privileges", "--pids-limit=64",
        "--cpus=1", "--memory=256m", "--memory-swap=256m",
        "--user=65534:65534", "--ipc=none",
        "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=16m,mode=1777",
        f"--mount=type=bind,source={folder},target=/app,readonly",
    ):
        assert mandatory in argv
    assert "--privileged" not in argv
    assert "--network=host" not in argv
    assert "host.docker.internal" not in " ".join(argv)
    assert "OPENAI_API_KEY" not in " ".join(argv)
    assert argv[argv.index(SHA)+1:] == ["python", "-I", "-c",
        "import sys;sys.path.insert(0,'/app');from tools.evie_distribution_worker import main;raise SystemExit(main())"]
    assert isolation_metadata(SHA)["networkMode"] == "none"
    with pytest.raises(ValueError):
        docker_command("python:latest", folder)


def test_minimal_capsule_excludes_registry_and_credentials(tmp_path):
    capsule = tmp_path / "capsule"
    capsule.mkdir()
    hashes = stage_capsule(capsule)
    assert set(hashes) == set(SOURCE_CAPSULE)
    names = {
        p.relative_to(capsule).as_posix()
        for p in capsule.rglob("*") if p.is_file()
    }
    assert len(names) == 8
    assert "app/modules/__init__.py" in names
    assert (capsule / "app/modules/__init__.py").read_bytes() == b""
    assert "app/settings.py" not in names
    assert ".env" not in names
    assert all((capsule / p).is_file() for p in SOURCE_CAPSULE)
    for p, digest in hashes.items():
        assert hashlib.sha256((capsule / p).read_bytes()).hexdigest() == digest


def test_missing_docker_refuses_without_spending_signed_lease(monkeypatch, approval):
    from tools import evie_isolated_distribution as isolated
    def no_image():
        raise ValueError("Docker unavailable, no fallback")
    monkeypatch.setattr(isolated, "image_preflight", no_image)
    with pytest.raises(ValueError, match="no fallback"):
        isolated.run_isolated_with_lease(**approval)
    assert not Path(approval["ledger"]).exists()
    assert not Path(approval["stage_dir"]).exists()


def test_docker_image_must_already_exist_and_be_content_addressed(monkeypatch):
    from tools import evie_container_runner as capsule
    monkeypatch.setattr(capsule.shutil, "which", lambda name: "/usr/bin/docker")
    monkeypatch.setattr(capsule.subprocess, "run", lambda *args, **kwargs:
        subprocess.CompletedProcess(args[0], 0, b"sha256:" + b"c"*64 + b"\n", b""))
    assert capsule.image_preflight() == "sha256:" + "c"*64
    monkeypatch.setattr(capsule.subprocess, "run", lambda *args, **kwargs:
        subprocess.CompletedProcess(args[0], 1, b"", b""))
    with pytest.raises(ValueError, match="not installed"):
        capsule.image_preflight()


def test_docker_signer_path_routes_real_distribution_result_without_fallback(monkeypatch, approval):
    from tools import evie_isolated_distribution as isolated
    monkeypatch.setattr(isolated, "image_preflight", lambda: SHA)
    seen = {}
    def simulated_container(topic, hooks, seconds, *, image_id):
        seen.update(topic=topic, count=len(hooks), timeout=seconds, image=image_id)
        # Mock backend only: CI test below invokes actual Docker.
        return dist._run_second_step(topic, hooks, seconds)
    monkeypatch.setattr(isolated, "run_isolated", simulated_container)
    result = isolated.run_isolated_with_lease(**approval)
    assert result["status"] == "second-stage-staged"
    assert result["containerIsolation"]["profile"] == PROFILE
    assert result["containerIsolation"]["networkMode"] == "none"
    assert result["containerIsolation"]["hostCheckoutMounted"] is False
    assert result["signedExecutionReceipt"] is False
    assert seen == {"topic": "EVIE Creator Loop", "count": 9,
                    "timeout": 20, "image": SHA}
    out = json.loads((Path(approval["stage_dir"]) / "distribution-draft.json").read_text())
    before = json.loads((Path(approval["hooks_dir"]) / "nine-hooks.json").read_text())
    assert out["hooks_used"] == before["hooks"][:5]


@pytest.mark.skipif(os.environ.get("EVIE_TEST_DOCKER") != "1",
                    reason="Real Docker runs only in explicit isolated CI lane")
def test_real_offline_container_runs_actual_signed_second_module(approval):
    image_id = image_preflight()
    result = run_isolated_with_lease(**approval)
    assert result["status"] == "second-stage-staged"
    assert result["containerIsolation"]["imageIdentity"] == image_id
    assert result["containerIsolation"]["networkMode"] == "none"
    assert result["containerIsolation"]["containerRootReadOnly"] is True
    assert result["publishingAuthorized"] is False
    assert result["signedExecutionReceipt"] is False
    artifacts = sorted(p.name for p in Path(approval["stage_dir"]).iterdir())
    assert artifacts == ["distribution-draft.json", "distribution-review-receipt.json",
                         "lease-consumption.json", "workflow-preflight.json"]
    final = json.loads((Path(approval["stage_dir"]) / "distribution-draft.json").read_text())
    source = json.loads((Path(approval["hooks_dir"]) / "nine-hooks.json").read_text())
    assert final["hooks_used"] == source["hooks"][:5]


@pytest.mark.skipif(os.environ.get("EVIE_TEST_DOCKER") != "1",
                    reason="Docker egress probe belongs only in opt-in isolated CI lane")
def test_docker_network_none_refuses_external_connect():
    image_id = image_preflight()
    command = [
        "docker", "run", "--rm", "--pull=never", "--network=none", "--read-only",
        "--cap-drop=ALL", "--security-opt=no-new-privileges",
        "--user=65534:65534", image_id, "python", "-I", "-c",
        "import socket,sys\n"
        "s=socket.socket()\n"
        "s.settimeout(2)\n"
        "try:\n"
        " s.connect(('1.1.1.1',443))\n"
        "except OSError:\n"
        " print('EGRESS_DENIED')\n"
        "else:\n"
        " sys.exit(2)\n",
    ]
    proc = subprocess.run(command, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=10, check=False)
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")[:250]
    assert b"EGRESS_DENIED" in proc.stdout
