"""R17: Docker-backed, narrow *distribution-only* source-capsule executor.

An OPTIONAL backend for R16 signed one-use leases. No general-purpose command
runner, host repo mounts, provider credentials, source registry, GPU or network.
Fails closed if a pre-existing local Python image / Docker daemon is absent.

Docker is an OS boundary, not a proof against privileged hosts, malicious Docker
daemon, Docker Desktop misconfiguration or kernel vulnerabilities.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.workflows.preflight import ROOT

PROFILE = "evie.docker-offline-capsule/1"
IMAGE = "python:3.11-slim"
IMAGE_ID = re.compile(r"^sha256:[a-f0-9]{64}$")
MAX_WORKER_OUTPUT = 60_000
SOURCE_CAPSULE = (
    "app/modules/base.py",
    "app/modules_v2/base.py",
    "app/modules_v2/distribution_generator.py",
    "tools/evie_distribution_worker.py",
)
EMPTY_INIT = (
    "app/__init__.py",
    "app/modules/__init__.py",  # DELIBERATELY not the real registry module.
    "app/modules_v2/__init__.py",
    "tools/__init__.py",
)
# Only this exact, reviewed Python expression is allowed inside the container.
ENTRY = (
    "import sys;sys.path.insert(0,'/app');"
    "from tools.evie_distribution_worker import main;"
    "raise SystemExit(main())"
)


def image_preflight(*, docker_binary: str = "docker") -> str:
    """Inspects a PREINSTALLED image. Does not pull images or contact registries."""
    if docker_binary != "docker":
        raise ValueError("only installed docker CLI is allowed")
    if not shutil.which("docker"):
        raise ValueError("Docker CLI missing; isolation is mandatory, no fallback")
    try:
        check = subprocess.run(
            ["docker", "image", "inspect", IMAGE, "--format", "{{.Id}}"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=5, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("local Docker image check failed") from exc
    if check.returncode != 0:
        raise ValueError("required local Python image not installed; no automatic pull")
    digest = check.stdout.decode("ascii", "strict").strip()
    if not IMAGE_ID.fullmatch(digest):
        raise ValueError("Docker image identity malformed")
    return digest


def stage_capsule(folder: Path) -> dict[str, str]:
    """Copy ONLY audited individual files, no source repo mount or secrets."""
    if not folder.is_dir() or folder.is_symlink():
        raise ValueError("invalid private capsule folder")
    files: dict[str, str] = {}
    for relative in SOURCE_CAPSULE:
        source = ROOT / relative
        if not source.is_file() or source.is_symlink() or not 0 < source.stat().st_size <= 64_000:
            raise ValueError("source capsule input invalid")
        blob = source.read_bytes()
        dest = folder / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(blob)
        dest.chmod(0o644)
        files[relative] = hashlib.sha256(blob).hexdigest()
    for relative in EMPTY_INIT:
        dest = folder / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Zero-byte package markers prevent importing registry.py, settings or providers.
        if relative != "app/modules_v2/__init__.py":
            dest.write_bytes(b"")
        else:
            source = ROOT / relative
            if not source.is_file() or source.is_symlink() or source.stat().st_size > 4096:
                raise ValueError("invalid v2 package marker")
            dest.write_bytes(source.read_bytes())
        dest.chmod(0o644)
    for parent in (folder / "app", folder / "app/modules",
                   folder / "app/modules_v2", folder / "tools"):
        parent.chmod(0o755)
    folder.chmod(0o755)
    return files


def docker_command(image_id: str, capsule: Path) -> list[str]:
    if not IMAGE_ID.fullmatch(image_id):
        raise ValueError("unapproved image identity")
    if not capsule.is_absolute() or not capsule.is_dir():
        raise ValueError("invalid temporary capsule mount")
    return [
        "docker", "run", "--rm", "--pull=never",
        "--network=none", "--read-only",
        "--cap-drop=ALL", "--security-opt=no-new-privileges",
        "--pids-limit=64", "--cpus=1", "--memory=256m", "--memory-swap=256m",
        "--user=65534:65534", "--ipc=none",
        "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=16m,mode=1777",
        f"--mount=type=bind,source={capsule},target=/app,readonly",
        "--workdir=/tmp", "--env=PYTHONDONTWRITEBYTECODE=1",
        image_id, "python", "-I", "-c", ENTRY,
    ]


def run_isolated(topic: str, hooks: list[str], timeout: int, *, image_id: str) -> dict:
    """Execute the SAME already-validated R15 worker in a restricted Docker box.

    Parent R15 still validates exact artifact format and SHA after this returns.
    """
    if type(timeout) is not int or not 1 <= timeout <= 20:
        raise ValueError("isolation timeout outside fixed 1–20s budget")
    if not isinstance(topic, str) or not isinstance(hooks, list) or len(hooks) != 9:
        raise ValueError("invalid bounded worker request")
    payload = json.dumps({"topic": topic, "hooks": hooks}).encode("utf-8")
    if len(payload) > 20_000:
        raise ValueError("worker request outside stdin limit")
    # Do NOT copy source checkout into Docker: expose only the 4 audited files.
    with tempfile.TemporaryDirectory(prefix="evie-capsule-") as temp:
        directory = Path(temp).absolute()
        source_hashes = stage_capsule(directory)
        command = docker_command(image_id, directory)
        try:
            proc = subprocess.run(
                command, input=payload, stdout=subprocess.PIPE,
                stderr=(subprocess.PIPE if os.environ.get("EVIE_TEST_DOCKER") == "1"
                            else subprocess.DEVNULL), timeout=timeout, check=False,
                # No repo/provider/API environment variables in the child Docker CLI.
                env={k: os.environ[k] for k in ("PATH", "SYSTEMROOT", "WINDIR", "HOME")
                     if k in os.environ},
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError("isolated worker could not complete within limit") from exc
        if proc.returncode != 0 or not 0 < len(proc.stdout) <= MAX_WORKER_OUTPUT:
            if os.environ.get("EVIE_TEST_DOCKER") == "1":
                # CI ONLY: synthetic fixture and public runner, never use with
                # private content. Remove this extra diagnostic after isolation
                # tests green; public CLI still returns only fixed error codes.
                trace = proc.stderr.decode("utf-8", "replace")[:1400]
                raise ValueError(
                    "Docker CI worker failure, exit=" + str(proc.returncode) +
                    " stdout=" + proc.stdout.decode("utf-8", "replace")[:500] +
                    " stderr=" + trace
                )
            raise ValueError("Docker capsule returned failure or oversized output")
        # Verify no source module changed on the host during Docker handoff.
        for relative, digest in source_hashes.items():
            if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != digest:
                raise ValueError("source changed while Docker capsule executed")
        try:
            report = json.loads(proc.stdout.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("Docker capsule did not emit valid JSON") from exc
        if not isinstance(report, dict) or report.get("schemaVersion") != "evie.distribution-worker/1":
            raise ValueError("Docker capsule worker contract invalid")
        return report


def isolation_metadata(image_id: str) -> dict:
    if not IMAGE_ID.fullmatch(image_id):
        raise ValueError("image identity malformed")
    return {
        "profile": PROFILE, "imageIdentity": image_id,
        "networkMode": "none",
        "containerRootReadOnly": True,
        "sourceCapsuleReadOnly": True,
        "hostCheckoutMounted": False,
        "capabilitiesDropped": True,
        "unprivilegedContainerUser": True,
        "pidsLimit": 64, "cpuLimit": 1, "memoryLimitMiB": 256,
        "privateTmpfsMiB": 16,
        "sandboxClaim": "docker-local-policy-observation-not-independent-host-attestation",
    }
