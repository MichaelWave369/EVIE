from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests


def _check_service(url: str, path: str, timeout: int = 2) -> tuple[bool, str]:
    try:
        r = requests.get(f"{url.rstrip('/')}{path}", timeout=timeout)
        if r.status_code == 200:
            return True, "reachable"
        return False, f"status={r.status_code}"
    except Exception as e:
        return False, str(e)


def run_readiness_checks() -> dict[str, Any]:
    checks: list[dict[str, str]] = []

    data_dir = Path(os.getenv("EV_DATA_DIR", "./data"))
    db_path = Path(os.getenv("EV_DB_PATH", str(data_dir / "embervault.db")))
    core_ok = True
    core_msg = "ok"
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        probe = data_dir / ".evie_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except Exception as e:
        core_ok = False
        core_msg = str(e)
    checks.append({"name": "core_paths", "status": "pass" if core_ok else "fail", "message": f"data_dir={data_dir}, db_dir={db_path.parent}, {core_msg}"})

    llm_backend = os.getenv("EV_LLM_BACKEND", "").strip().lower()
    llm_status, llm_msg = "warn", "EV_LLM_BACKEND not set"
    if llm_backend == "openai":
        llm_status = "pass" if bool(os.getenv("EV_OPENAI_API_KEY")) else "warn"
        llm_msg = "openai key detected" if llm_status == "pass" else "EV_OPENAI_API_KEY missing"
    elif llm_backend == "anthropic":
        llm_status = "pass" if bool(os.getenv("EV_ANTHROPIC_API_KEY")) else "warn"
        llm_msg = "anthropic key detected" if llm_status == "pass" else "EV_ANTHROPIC_API_KEY missing"
    elif llm_backend == "ollama":
        base = os.getenv("EV_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        ok, msg = _check_service(base, "/api/tags")
        llm_status = "pass" if ok else "warn"
        llm_msg = f"ollama {msg}"
    checks.append({"name": "llm_backend", "status": llm_status, "message": f"backend={llm_backend or 'unset'}; {llm_msg}"})

    emb = os.getenv("EV_EMBED_BACKEND", "hash").strip().lower()
    emb_status, emb_msg = "pass", "hash backend local"
    if emb == "openai":
        emb_status = "pass" if bool(os.getenv("EV_OPENAI_API_KEY")) else "warn"
        emb_msg = "openai key detected" if emb_status == "pass" else "EV_OPENAI_API_KEY missing"
    elif emb == "ollama":
        base = os.getenv("EV_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        ok, msg = _check_service(base, "/api/tags")
        emb_status = "pass" if ok else "warn"
        emb_msg = f"ollama {msg}"
    checks.append({"name": "embeddings_backend", "status": emb_status, "message": f"backend={emb}; {emb_msg}"})

    comfy_url = os.getenv("EV_COMFYUI_URL", "http://127.0.0.1:8188")
    ok, msg = _check_service(comfy_url, "/system_stats")
    checks.append({"name": "comfyui", "status": "pass" if ok else "warn", "message": f"{comfy_url} {msg}"})

    bridge_url = os.getenv("EV_VISUAL_FX_BRIDGE_URL", "http://127.0.0.1:18888")
    ok, msg = _check_service(bridge_url, "/health")
    checks.append({"name": "visual_fx_bridge", "status": "pass" if ok else "warn", "message": f"{bridge_url} {msg}"})

    checks.append({"name": "gumroad_credentials", "status": "pass" if bool(os.getenv("EV_GUMROAD_ACCESS_TOKEN")) else "warn", "message": "token present" if os.getenv("EV_GUMROAD_ACCESS_TOKEN") else "EV_GUMROAD_ACCESS_TOKEN missing"})
    checks.append({"name": "youtube_credentials", "status": "pass" if bool(os.getenv("EV_YOUTUBE_ACCESS_TOKEN")) else "warn", "message": "token present" if os.getenv("EV_YOUTUBE_ACCESS_TOKEN") else "EV_YOUTUBE_ACCESS_TOKEN missing"})

    openai_key = bool(os.getenv("EV_OPENAI_API_KEY"))
    openai_image = os.getenv("EV_OPENAI_IMAGE_MODEL", "").strip()
    checks.append({
        "name": "openai_image_fallback",
        "status": "pass" if (openai_key and openai_image) else "warn",
        "message": "configured" if (openai_key and openai_image) else "EV_OPENAI_API_KEY/EV_OPENAI_IMAGE_MODEL not fully configured",
    })

    has_fail = any(c["status"] == "fail" for c in checks)
    has_warn = any(c["status"] == "warn" for c in checks)
    overall = "fail" if has_fail else ("warn" if has_warn else "pass")
    return {"overall": overall, "checks": checks}
