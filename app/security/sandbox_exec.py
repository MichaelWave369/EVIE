from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import os
import subprocess
import sys
import tempfile

from app.settings import settings


class SandboxError(RuntimeError):
    pass


@dataclass
class SandboxConfig:
    # subprocess: portable, fast
    # docker: stronger isolation (network none + cpu/mem limits); requires Docker installed
    mode: str = "subprocess"   # subprocess|docker
    python_exe: str = sys.executable
    timeout_seconds: int = 30
    work_root: str = "data/sandboxes"
    env_allowlist: Optional[List[str]] = None

    # docker settings
    docker_image: str = "python:3.11-slim"
    docker_network: str = "none"
    docker_cpus: str = "0.50"
    docker_memory: str = "512m"
    docker_read_only: bool = False
    docker_extra_args: Optional[List[str]] = None


def config_from_settings() -> SandboxConfig:
    allow = (getattr(settings, "sandbox_env_allowlist", "PATH,PYTHONPATH") or "").strip()
    env_allow = [x.strip() for x in allow.split(",") if x.strip()] or ["PATH", "PYTHONPATH"]
    return SandboxConfig(
        mode=str(getattr(settings, "sandbox_mode", "subprocess")),
        python_exe=sys.executable,
        timeout_seconds=int(getattr(settings, "sandbox_timeout_seconds", 30)),
        work_root=str(getattr(settings, "sandbox_work_root", Path("./data/sandboxes"))),
        env_allowlist=env_allow,
        docker_image=str(getattr(settings, "sandbox_docker_image", "python:3.11-slim")),
        docker_network=str(getattr(settings, "sandbox_docker_network", "none")),
        docker_cpus=str(getattr(settings, "sandbox_docker_cpus", "0.50")),
        docker_memory=str(getattr(settings, "sandbox_docker_memory", "512m")),
        docker_read_only=bool(getattr(settings, "sandbox_docker_read_only", False)),
        docker_extra_args=None,
    )


def _filter_env(cfg: SandboxConfig) -> Dict[str, str]:
    keep = cfg.env_allowlist or ["PATH", "PYTHONPATH"]
    out: Dict[str, str] = {}
    for k in keep:
        if k in os.environ:
            out[k] = os.environ[k]
    # Hard-disable proxies unless explicitly allowed
    for k in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"]:
        out.pop(k, None)
    return out


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    # app/security/sandbox_exec.py -> repo root is two levels up
    return here.parents[2]


def run_worker_json(module: str, payload: Dict[str, Any], cfg: Optional[SandboxConfig] = None) -> Dict[str, Any]:
    """Run a python module as an isolated worker process, exchanging JSON via stdin/stdout."""
    cfg = cfg or config_from_settings()
    Path(cfg.work_root).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="evie_sb_", dir=cfg.work_root) as td:
        if cfg.mode == "docker":
            return _run_docker(module, payload, cfg, td)
        return _run_subprocess(module, payload, cfg, td)


def _run_subprocess(module: str, payload: Dict[str, Any], cfg: SandboxConfig, td: str) -> Dict[str, Any]:
    cmd = [cfg.python_exe, "-m", module]
    env = _filter_env(cfg)
    env["EVIE_SANDBOX_DIR"] = td
    try:
        p = subprocess.run(
            cmd,
            input=json.dumps(payload).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=td,
            env=env,
            timeout=cfg.timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise SandboxError(f"sandbox timeout after {cfg.timeout_seconds}s for {module}")

    if p.returncode != 0:
        raise SandboxError(f"sandbox error rc={p.returncode}: {p.stderr.decode('utf-8', errors='ignore')[:900]}")

    out = p.stdout.decode("utf-8", errors="ignore").strip()
    try:
        return json.loads(out) if out else {}
    except Exception as e:
        raise SandboxError(
            f"sandbox returned non-json: {e}. stdout={out[:400]} stderr={p.stderr.decode('utf-8', errors='ignore')[:200]}"
        )


def _docker_available() -> bool:
    try:
        p = subprocess.run(["docker", "version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5, check=False)
        return p.returncode == 0
    except Exception:
        return False


def _run_docker(module: str, payload: Dict[str, Any], cfg: SandboxConfig, td: str) -> Dict[str, Any]:
    if not _docker_available():
        raise SandboxError("docker mode requested but docker is not available on this host")

    repo = _repo_root()
    env = _filter_env(cfg)
    env["PYTHONPATH"] = "/app"
    env["EVIE_SANDBOX_DIR"] = "/work"

    cmd = [
        "docker",
        "run",
        "--rm",
        "-i",
        "--network",
        str(cfg.docker_network),
        "--cpus",
        str(cfg.docker_cpus),
        "-m",
        str(cfg.docker_memory),
        "-v",
        f"{str(repo)}:/app:ro",
        "-v",
        f"{td}:/work:rw",
        "-w",
        "/work",
    ]
    if cfg.docker_read_only:
        cmd.append("--read-only")
        cmd += ["--tmpfs", "/tmp:rw,size=64m"]

    for k, v in env.items():
        cmd += ["-e", f"{k}={v}"]

    if cfg.docker_extra_args:
        cmd += [str(x) for x in cfg.docker_extra_args]

    cmd += [str(cfg.docker_image), "python", "-m", module]

    try:
        p = subprocess.run(
            cmd,
            input=json.dumps(payload).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=cfg.timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise SandboxError(f"docker sandbox timeout after {cfg.timeout_seconds}s for {module}")

    if p.returncode != 0:
        err = p.stderr.decode("utf-8", errors="ignore")
        raise SandboxError(f"docker sandbox error rc={p.returncode}: {err[:900]}")

    out = p.stdout.decode("utf-8", errors="ignore").strip()
    try:
        return json.loads(out) if out else {}
    except Exception as e:
        raise SandboxError(
            f"docker sandbox returned non-json: {e}. stdout={out[:400]} stderr={p.stderr.decode('utf-8', errors='ignore')[:200]}"
        )
