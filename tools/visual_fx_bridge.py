from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from app.modules_v2.visual_final_assets import set_preferred_asset

StatusType = Literal[
    "created",
    "queued",
    "awaiting_external_processing",
    "running",
    "output_detected",
    "completed",
    "failed",
    "cancelled",
]


class JobCreate(BaseModel):
    tool_name: str
    source_workflow: str = ""
    source_run_id: str = ""
    asset_type: str = ""
    prompts_used: list[str] = Field(default_factory=list)
    ranking_notes: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    input_paths: list[str] = Field(default_factory=list)
    output_paths: list[str] = Field(default_factory=list)
    notes: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    job_type: str = ""




class JobApprove(BaseModel):
    category: str = ""
    asset_path: str = ""
    note: str = ""
    mark_completed: bool = True

class JobComplete(BaseModel):
    status: Literal["completed", "failed", "cancelled"] = "completed"
    output_paths: list[str] = Field(default_factory=list)
    notes: str = ""
    ranking_notes: list[str] = Field(default_factory=list)


BASE_DIR = Path(os.getenv("EV_VISUAL_FX_BRIDGE_DIR", "data/visual_fx_bridge")).resolve()
JOBS_DIR = BASE_DIR / "jobs"
JOBS_DIR.mkdir(parents=True, exist_ok=True)

TOOL_TO_EXE_ENV = {
    "vision_fx": "EV_VISION_FX_EXE",
    "render_fx": "EV_RENDER_FX_EXE",
    "vector_fx": "EV_VECTOR_FX_EXE",
}

AUTO_COMPLETE_ON_OUTPUT = str(os.getenv("EV_VISUAL_FX_AUTO_COMPLETE_ON_OUTPUT", "false")).strip().lower() in {"1", "true", "yes", "on"}
VALID_OUTPUT_EXTS = {ext.strip().lower() for ext in (os.getenv("EV_VISUAL_FX_OUTPUT_EXTS", ".png,.jpg,.jpeg,.webp,.svg,.pdf,.json,.txt,.md").split(",")) if ext.strip()}

app = FastAPI(title="EVIE Visual FX Bridge", version="0.1.0")


def _now() -> str:
    return datetime.utcnow().isoformat()


def _job_dir(job_id: str) -> Path:
    return JOBS_DIR / job_id


def _meta_path(job_id: str) -> Path:
    return _job_dir(job_id) / "meta.json"


def _status_path(job_id: str) -> Path:
    return _job_dir(job_id) / "status.json"


def _log_path(job_id: str) -> Path:
    return _job_dir(job_id) / "logs.txt"


def _append_log(job_id: str, message: str) -> None:
    _log_path(job_id).parent.mkdir(parents=True, exist_ok=True)
    with _log_path(job_id).open("a", encoding="utf-8") as f:
        f.write(f"[{_now()}] {message}\n")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _copy_inputs(job_id: str, input_paths: list[str]) -> list[str]:
    input_dir = _job_dir(job_id) / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for raw in input_paths:
        src = Path(raw)
        if not src.exists() or not src.is_file():
            _append_log(job_id, f"Input not copied (missing/non-file): {raw}")
            continue
        dst = input_dir / src.name
        if dst.exists():
            dst = input_dir / f"{src.stem}_{uuid.uuid4().hex[:6]}{src.suffix}"
        shutil.copy2(src, dst)
        copied.append(str(dst))
    return copied


def _scan_outputs(job_id: str) -> list[str]:
    out_dir = _job_dir(job_id) / "output"
    if not out_dir.exists():
        return []
    return [str(p) for p in sorted(out_dir.glob("**/*")) if p.is_file()]


def _filter_valid_outputs(paths: list[str]) -> list[str]:
    valid: list[str] = []
    for raw in paths:
        p = Path(raw)
        if p.is_file() and (not VALID_OUTPUT_EXTS or p.suffix.lower() in VALID_OUTPUT_EXTS):
            valid.append(str(p))
    return valid


def _detect_and_maybe_transition(job_id: str) -> dict[str, Any]:
    meta = _read_json(_meta_path(job_id))
    if not meta:
        return {}
    current_status = str(meta.get("status") or "")
    outputs = _filter_valid_outputs(_scan_outputs(job_id))
    if not outputs:
        return {"detected_outputs": []}

    meta["output_paths"] = outputs
    meta["updated_at"] = _now()
    if AUTO_COMPLETE_ON_OUTPUT and current_status in {"awaiting_external_processing", "queued", "running", "output_detected"}:
        meta["status"] = "completed"
        _write_json(_meta_path(job_id), meta)
        _set_status(job_id, "completed", "Auto-completed after output detection")
        return {"detected_outputs": outputs, "auto_completed": True}

    if current_status in {"awaiting_external_processing", "queued", "running"}:
        meta["status"] = "output_detected"
        _write_json(_meta_path(job_id), meta)
        _set_status(job_id, "output_detected", "Output files detected; ready to complete")
    else:
        _write_json(_meta_path(job_id), meta)
    return {"detected_outputs": outputs, "auto_completed": False}


def _launch_exe_if_configured(job_id: str, tool_name: str) -> dict[str, Any]:
    env_key = TOOL_TO_EXE_ENV.get(tool_name)
    if not env_key:
        return {"launched": False, "reason": "no_env_mapping"}
    exe_path = os.getenv(env_key, "").strip()
    if not exe_path:
        _append_log(job_id, f"{env_key} not configured; manual processing required.")
        return {"launched": False, "reason": f"{env_key} not configured"}
    p = Path(exe_path)
    if not p.exists():
        _append_log(job_id, f"Configured EXE not found: {exe_path}")
        return {"launched": False, "reason": "exe_path_missing", "exe_path": exe_path}

    try:
        subprocess.Popen([str(p)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _append_log(job_id, f"Launched {tool_name} EXE ({exe_path}) as convenience only.")
        _append_log(job_id, "Job remains awaiting_external_processing until output is provided and completed.")
        return {"launched": True, "exe_path": exe_path}
    except Exception as e:
        _append_log(job_id, f"EXE launch failed: {e}")
        return {"launched": False, "reason": str(e), "exe_path": exe_path}


def _build_job_payload(job_id: str, req: JobCreate) -> dict[str, Any]:
    created = _now()
    copied_inputs = _copy_inputs(job_id, req.input_paths)
    payload = {
        "job_id": job_id,
        "tool_name": req.tool_name,
        "created_at": created,
        "updated_at": created,
        "status": "created",
        "source_workflow": req.source_workflow,
        "source_run_id": req.source_run_id,
        "asset_type": req.asset_type,
        "prompts_used": req.prompts_used,
        "ranking_notes": req.ranking_notes,
        "expected_outputs": req.expected_outputs,
        "input_paths": copied_inputs,
        "output_paths": req.output_paths,
        "notes": req.notes,
        "metadata": req.metadata,
        "job_type": req.job_type,
        "job_folder": str(_job_dir(job_id)),
        "input_folder": str(_job_dir(job_id) / "input"),
        "output_folder": str(_job_dir(job_id) / "output"),
    }
    return payload


def _set_status(job_id: str, status: StatusType, detail: str = "") -> dict[str, Any]:
    meta = _read_json(_meta_path(job_id))
    if not meta:
        raise HTTPException(status_code=404, detail=f"job not found: {job_id}")
    status_obj = {
        "job_id": job_id,
        "status": status,
        "updated_at": _now(),
        "detail": detail,
    }
    meta["status"] = status
    meta["updated_at"] = status_obj["updated_at"]
    _write_json(_meta_path(job_id), meta)
    _write_json(_status_path(job_id), status_obj)
    _append_log(job_id, f"Status set to {status}. {detail}".strip())
    return status_obj


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "service": "visual_fx_bridge", "jobs_dir": str(JOBS_DIR), "time": _now()}


@app.get("/jobs")
def list_jobs(limit: int = Query(default=20, ge=1, le=200)) -> dict[str, Any]:
    metas = []
    for meta_file in JOBS_DIR.glob("*/meta.json"):
        jid = meta_file.parent.name
        _detect_and_maybe_transition(jid)
        m = _read_json(meta_file)
        if m:
            m["detected_outputs_count"] = len(_filter_valid_outputs(_scan_outputs(jid)))
            metas.append(m)
    metas.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return {"jobs": metas[:limit], "count": len(metas)}


@app.post("/jobs", status_code=201)
def create_job(req: JobCreate) -> dict[str, Any]:
    job_id = uuid.uuid4().hex[:12]
    jdir = _job_dir(job_id)
    (jdir / "input").mkdir(parents=True, exist_ok=True)
    (jdir / "output").mkdir(parents=True, exist_ok=True)

    payload = _build_job_payload(job_id, req)
    _write_json(_meta_path(job_id), payload)
    _write_json(_status_path(job_id), {"job_id": job_id, "status": "created", "updated_at": payload["created_at"]})
    _append_log(job_id, f"Job created for tool: {req.tool_name}")

    _set_status(job_id, "queued", "Queued for handoff")
    launch_info = _launch_exe_if_configured(job_id, req.tool_name)
    _set_status(job_id, "awaiting_external_processing", "Waiting for manual or external completion")

    current = _read_json(_meta_path(job_id))
    current["launch"] = launch_info
    _write_json(_meta_path(job_id), current)
    return current


@app.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    meta = _read_json(_meta_path(job_id))
    if not meta:
        raise HTTPException(status_code=404, detail=f"job not found: {job_id}")
    detect = _detect_and_maybe_transition(job_id)
    meta = _read_json(_meta_path(job_id))
    status_obj = _read_json(_status_path(job_id))
    return {"job": meta, "status": status_obj, "detected_outputs": detect.get("detected_outputs") or _filter_valid_outputs(_scan_outputs(job_id)), "auto_completed": bool(detect.get("auto_completed"))}


@app.post("/jobs/{job_id}/complete")
def complete_job(job_id: str, req: JobComplete) -> dict[str, Any]:
    meta = _read_json(_meta_path(job_id))
    if not meta:
        raise HTTPException(status_code=404, detail=f"job not found: {job_id}")

    detected = _scan_outputs(job_id)
    output_paths = req.output_paths or detected
    if output_paths:
        meta["output_paths"] = output_paths
    if req.notes:
        meta["notes"] = ((meta.get("notes") or "") + "\n" + req.notes).strip()
    if req.ranking_notes:
        meta["ranking_notes"] = list(meta.get("ranking_notes") or []) + list(req.ranking_notes)
    meta["updated_at"] = _now()
    meta["status"] = req.status
    _write_json(_meta_path(job_id), meta)
    if req.status == "completed":
        meta_md = meta.get("metadata") if isinstance(meta.get("metadata"), dict) else {}
        fas = str(meta_md.get("final_assets_state_path") or "")
        fac = str(meta_md.get("final_asset_category") or "")
        ap = (meta.get("output_paths") or [""])[0]
        if fas and fac and ap:
            set_preferred_asset(fas, category=fac, asset_path=ap, source="visual_fx_bridge.complete", note="Auto-promoted first completed output")
            meta["approved_final_asset"] = ap
            _write_json(_meta_path(job_id), meta)

    status_obj = _set_status(job_id, req.status, "Completed via API")
    return {"job": meta, "status": status_obj}


@app.post("/vision-fx/handoff", status_code=201)
def vision_fx_handoff(req: JobCreate) -> dict[str, Any]:
    req.tool_name = "vision_fx"
    return create_job(req)


@app.post("/render-fx/handoff", status_code=201)
def render_fx_handoff(req: JobCreate) -> dict[str, Any]:
    req.tool_name = "render_fx"
    return create_job(req)


@app.post("/vector-fx/handoff", status_code=201)
def vector_fx_handoff(req: JobCreate) -> dict[str, Any]:
    req.tool_name = "vector_fx"
    return create_job(req)


@app.post("/jobs/{job_id}/approve")
def approve_job_asset(job_id: str, req: JobApprove) -> dict[str, Any]:
    meta = _read_json(_meta_path(job_id))
    if not meta:
        raise HTTPException(status_code=404, detail=f"job not found: {job_id}")

    md = meta.get("metadata") if isinstance(meta.get("metadata"), dict) else {}
    category = str(req.category or md.get("final_asset_category") or "").strip()
    if not category:
        raise HTTPException(status_code=400, detail="category is required (or metadata.final_asset_category must be set)")

    candidate = str(req.asset_path or "").strip()
    if not candidate:
        detected = _filter_valid_outputs(_scan_outputs(job_id))
        candidate = detected[0] if detected else ""
    if not candidate:
        raise HTTPException(status_code=400, detail="No asset_path provided and no output files detected")

    state_path = str(md.get("final_assets_state_path") or (_job_dir(job_id) / "approved_final_assets.json"))
    state = set_preferred_asset(state_path, category=category, asset_path=candidate, source="visual_fx_bridge.approve", note=req.note or "Approved via bridge")

    meta["approved_final_asset"] = candidate
    meta["approved_category"] = category
    meta["updated_at"] = _now()
    _write_json(_meta_path(job_id), meta)

    if req.mark_completed and str(meta.get("status")) not in {"completed", "failed", "cancelled"}:
        _set_status(job_id, "completed", "Marked completed after final asset approval")

    return {"job": _read_json(_meta_path(job_id)), "approved_state_path": state_path, "preferred_assets": state.get("preferred_assets", {})}


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("EV_VISUAL_FX_BRIDGE_HOST", "127.0.0.1")
    port = int(os.getenv("EV_VISUAL_FX_BRIDGE_PORT", "18888"))
    uvicorn.run("tools.visual_fx_bridge:app", host=host, port=port, reload=False)
