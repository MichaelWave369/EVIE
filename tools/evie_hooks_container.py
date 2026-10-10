"""R19 fixed hook-generator Docker source capsule, exclusively for governed Stage 1.

Reuses R17's audited Docker hardening profile and local content-addressed image.
No host Python fallback in the R18 controller. The older independent R14
host-processor remains unchanged for backward compatibility.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

from app.workflows.preflight import ROOT
from tools.evie_container_runner import (
    IMAGE_ID, EMPTY_INIT, MAX_WORKER_OUTPUT,
    docker_command, image_preflight as image_preflight,
)

PROFILE = "evie.docker-hooks-capsule/1"
HOOK_ENTRY = (
    "import sys;sys.path.insert(0,'/app');"
    "from tools.evie_hooks_worker import main;"
    "raise SystemExit(main())"
)
HOOK_FILES = (
    "app/modules/base.py",
    "app/modules_v2/base.py",
    "app/modules_v2/hooks_generator.py",
    "tools/evie_hooks_worker.py",
)


def stage_hooks_capsule(folder: Path) -> dict[str, str]:
    """Only four required public source files and empty package markers."""
    if not folder.is_dir() or folder.is_symlink():
        raise ValueError("invalid isolated hooks capsule")
    hashes = {}
    for relative in HOOK_FILES:
        src = ROOT / relative
        if not src.is_file() or src.is_symlink() or not 0 < src.stat().st_size <= 64_000:
            raise ValueError("hooks capsule source refused")
        data = src.read_bytes()
        target = folder / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(0o644)
        hashes[relative] = hashlib.sha256(data).hexdigest()
    for relative in EMPTY_INIT:
        dest = folder / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        if relative != "app/modules_v2/__init__.py":
            data = b""
        else:
            src = ROOT / relative
            if src.is_symlink() or not src.is_file() or src.stat().st_size > 4096:
                raise ValueError("unsupported v2 package marker")
            data = src.read_bytes()
        dest.write_bytes(data)
        dest.chmod(0o644)
    for path in ("app", "app/modules", "app/modules_v2", "tools"):
        (folder / path).chmod(0o755)
    folder.chmod(0o755)
    return hashes


def run_hooks_isolated(topic: str, script: str, seconds: int, *, image_id: str) -> dict:
    """Invoke the real R14 worker using stdin in fixed R17 Docker conditions."""
    if type(seconds) is not int or not 1 <= seconds <= 20:
        raise ValueError("isolated hooks timeout outside 1–20 seconds")
    if not IMAGE_ID.fullmatch(image_id):
        raise ValueError("untrusted runtime image identity")
    if not isinstance(topic, str) or not 1 <= len(topic) <= 80 or \
            not all(c.isalnum() or c in " -_" for c in topic):
        raise ValueError("unsupported isolated topic")
    if not isinstance(script, str) or not 20 <= len(script.encode("utf-8")) <= 8192:
        raise ValueError("script violates isolated input budget")
    payload = json.dumps({"topic": topic, "script": script}).encode("utf-8")
    if len(payload) > 10_000:
        raise ValueError("isolated input transport budget exceeded")
    with tempfile.TemporaryDirectory(prefix="evie-hooks-capsule-") as root:
        directory = Path(root).absolute()
        source_shas = stage_hooks_capsule(directory)
        argv = docker_command(image_id, directory)
        if argv[-1] != (
            "import sys;sys.path.insert(0,'/app');"
            "from tools.evie_distribution_worker import main;"
            "raise SystemExit(main())"
        ):
            raise ValueError("unexpected Docker worker entrypoint")
        argv[-1] = HOOK_ENTRY
        try:
            child = subprocess.run(
                argv, input=payload, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, timeout=seconds, check=False,
                env={name: os.environ[name]
                     for name in ("PATH", "SYSTEMROOT", "WINDIR", "HOME")
                     if name in os.environ},
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            raise ValueError("isolated hooks worker failed its time budget") from exc
        if child.returncode != 0 or not 0 < len(child.stdout) <= MAX_WORKER_OUTPUT:
            raise ValueError("isolated hooks worker failed or exceeded output budget")
        for relative, previous in source_shas.items():
            if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != previous:
                raise ValueError("hooks capsule source changed during execution")
        try:
            result = json.loads(child.stdout.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("isolated hooks did not emit valid JSON") from exc
        if not isinstance(result, dict) or result.get("schemaVersion") != "evie.supervised-hooks-worker/1":
            raise ValueError("isolated worker response malformed")
        return result


def isolation_metadata(image_id: str) -> dict:
    if not IMAGE_ID.fullmatch(image_id):
        raise ValueError("invalid hooks image identity")
    return {
        "profile": PROFILE,
        "imageIdentity": image_id,
        "networkMode": "none",
        "containerRootReadOnly": True,
        "hostCheckoutMounted": False,
        "sourceCapsuleReadOnly": True,
        "capabilitiesDropped": True,
        "user": "65534:65534",
        "pidsLimit": 64,
        "cpuLimit": 1,
        "memoryLimitMiB": 256,
        "privateTmpfsMiB": 16,
        "note": "Local Docker launch-policy observation, not authenticated host attestation.",
    }
