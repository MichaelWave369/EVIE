from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any

from app.settings import settings
from app.security.sandbox_exec import run_worker_json, SandboxError


@dataclass
class CodeGateResult:
    ok: bool
    ran: bool
    details: Dict[str, Any]


def _has_py(artifact_paths: List[str]) -> bool:
    for p in artifact_paths or []:
        try:
            pp = Path(p)
            if pp.is_file() and pp.suffix.lower() == ".py":
                return True
            if pp.is_dir() and any(pp.rglob("*.py")):
                return True
        except Exception:
            continue
    return False


def run_code_gate(artifact_paths: List[str]) -> CodeGateResult:
    """Best-effort code safety gate.

    If any .py files exist in the artifacts, run py_compile in a sandbox.
    This does NOT execute the code; it only compiles/parses.
    """
    if not getattr(settings, "sandbox_enabled", True):
        return CodeGateResult(ok=True, ran=False, details={"disabled": True})

    if not artifact_paths or not _has_py(artifact_paths):
        return CodeGateResult(ok=True, ran=False, details={"python_files": 0})

    try:
        res = run_worker_json("app.workers.python_compile_worker", {"paths": artifact_paths})
        return CodeGateResult(ok=bool(res.get("ok")), ran=True, details=res)
    except SandboxError as e:
        # sandbox failures are treated as warnings to avoid blocking on missing docker
        return CodeGateResult(ok=True, ran=False, details={"sandbox_error": str(e), "soft_fail": True})
