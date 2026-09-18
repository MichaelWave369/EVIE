from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from app.security.auth import require_api_key
from app.modules import REGISTRY
from app.modules.specs import build_specs
from app.db import queries
from app.security.sandbox import validate_artifacts
from app.qa.code_safety_gate import run_code_gate
from app.scheduler.jobs import enqueue_task

router = APIRouter(prefix="/v1/modules", tags=["modules"])

class GenerateReq(BaseModel):
    topic: str
    constraints: Dict[str, Any] = {}
    async_run: bool = False  # if true, enqueue in local scheduler

@router.get("", dependencies=[Depends(require_api_key)])
def list_modules():
    return {"modules": sorted(REGISTRY.keys())}

@router.get("/specs", dependencies=[Depends(require_api_key)])
def module_specs():
    return {"specs": build_specs()}

@router.post("/{module_name}/generate", dependencies=[Depends(require_api_key)])
def generate(module_name: str, req: GenerateReq):
    m = REGISTRY.get(module_name)
    if not m:
        raise HTTPException(status_code=404, detail=f"Unknown module: {module_name}")

    # Create run record (observability)
    run_id = queries.create_run(
        run_type="module",
        module=module_name,
        topic=req.topic,
        input_obj={"topic": req.topic, "constraints": req.constraints, "async": bool(req.async_run)},
        actor="api",
    )

    if req.async_run:
        # schedule task for local worker
        payload = {"topic": req.topic, "constraints": req.constraints, "run_id": run_id}
        task_id = enqueue_task(module=module_name, task_type="module_generate", payload=payload, schedule_at=None, run_id=run_id)
        return {"ok": True, "queued": True, "run_id": run_id, "task_id": task_id}

    step_id = queries.create_run_step(run_id=run_id, step_index=0, step_type="module", module=module_name, input_obj={"topic": req.topic, "constraints": req.constraints})
    try:
        res = m.generate(req.topic, req.constraints)
        chk = validate_artifacts(res.artifact_paths)
        if not chk.ok:
            raise ValueError("Artifact validation failed: " + "; ".join(chk.problems[:10]))

        code_gate = run_code_gate(res.artifact_paths)
        if not code_gate.ok:
            raise ValueError("Code safety gate failed")

        out = {"module": module_name, "artifact_paths": res.artifact_paths, "metadata": res.metadata, "validation": chk.__dict__, "code_gate": code_gate.__dict__}
        queries.finish_run_step(step_id, status="done", output_obj=out, error=None)
        queries.finish_run(run_id, status="done", output_obj=out, error=None)
        return {"run_id": run_id, **out}
    except Exception as e:
        queries.finish_run_step(step_id, status="error", output_obj={}, error=str(e))
        queries.finish_run(run_id, status="error", output_obj={}, error=str(e))
        raise
