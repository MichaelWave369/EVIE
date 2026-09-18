from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional, List

from app.security.auth import require_api_key
from app.swarm.director import make_plan
from app.swarm.memory import load as mem_load, append_note, set_state, reset as mem_reset
from app.db import queries
from app.workflows.runner import run_workflow
from app.modules import REGISTRY
from app.security.sandbox import validate_artifacts
from app.qa.code_safety_gate import run_code_gate

router = APIRouter(prefix="/v1/swarm", tags=["swarm"])


class PlanReq(BaseModel):
    goal: str
    topic: Optional[str] = None
    constraints: Dict[str, Any] = {}
    campaign_id: Optional[int] = None
    session_id: Optional[int] = None
    prefer_backend: Optional[str] = None  # heuristic | ollama


@router.post("/plan", dependencies=[Depends(require_api_key)])
def plan(req: PlanReq):
    # Ensure we have a session to bind agent memory + evidence
    session_id = req.session_id
    if session_id is None:
        # Create a lightweight session record for auditability
        try:
            session_id = queries.create_session(req.campaign_id, name=(req.topic or req.goal or "Swarm Session")[:120])
        except Exception:
            session_id = None

    pl = make_plan(goal=req.goal, topic=req.topic, constraints=req.constraints, prefer_backend=req.prefer_backend)

    run_id = queries.create_run(
        run_type="swarm_plan",
        module="swarm_director",
        topic=req.topic or req.goal,
        input_obj={"goal": req.goal, "topic": req.topic, "constraints": req.constraints, "campaign_id": req.campaign_id, "session_id": session_id},
        actor="api",
        campaign_id=req.campaign_id,
        session_id=session_id,
    )
    queries.finish_run(run_id, status="done", output_obj={"plan": pl.to_dict()}, error=None)

    # Store a director note in agent memory
    if session_id is not None:
        append_note(int(session_id), "director", f"Planned workflow={pl.workflow} backend={pl.director_backend}", meta={"confidence": pl.confidence})

    return {"plan_id": run_id, "session_id": session_id, "plan": pl.to_dict()}


class RunReq(BaseModel):
    # Either supply a plan_id from /plan, or inline plan fields.
    plan_id: Optional[int] = None
    goal: Optional[str] = None
    topic: Optional[str] = None
    workflow: Optional[str] = None
    steps: List[Dict[str, Any]] = []
    constraints: Dict[str, Any] = {}
    campaign_id: Optional[int] = None
    session_id: Optional[int] = None
    dry_run: bool = False


@router.post("/run", dependencies=[Depends(require_api_key)])
def run(req: RunReq):
    # Load plan from plan_id if provided
    workflow = req.workflow
    steps = req.steps or []
    topic = req.topic or req.goal or "Untitled"

    if req.plan_id is not None:
        try:
            pr = queries.get_run(int(req.plan_id))
            plan = (pr.get("output") or {}).get("plan") or {}
            if isinstance(plan, dict):
                workflow = plan.get("workflow") or workflow
                steps = plan.get("steps") or steps
                topic = plan.get("topic") or topic
                # inherit campaign/session if absent
                req.campaign_id = req.campaign_id or pr.get("campaign_id")
                req.session_id = req.session_id or pr.get("session_id")
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"plan_id not found: {e}")

    # If we have a workflow, prefer running it via workflow engine (which adds step run records).
    if workflow:
        res = run_workflow(
            workflow,
            topic=topic,
            constraints=req.constraints,
            actor="swarm",
            campaign_id=req.campaign_id,
            session_id=req.session_id,
            dry_run=req.dry_run,
        )
        if req.session_id is not None:
            append_note(int(req.session_id), "director", f"Executed workflow={workflow}", meta={"run_id": res.get("run_id")})
        return {"mode": "workflow", **res}

    # Else: explicit step list (module-by-module)
    if not steps:
        raise HTTPException(status_code=400, detail="No workflow or steps provided")

    run_id = queries.create_run(
        run_type="swarm_run",
        module="swarm_steps",
        topic=topic,
        input_obj={"topic": topic, "constraints": req.constraints, "steps": steps},
        actor="swarm",
        campaign_id=req.campaign_id,
        session_id=req.session_id,
    )

    outputs: List[Dict[str, Any]] = []
    if req.dry_run:
        for i, s in enumerate(steps):
            mod = (s or {}).get("module")
            outputs.append({"step": i, "module": mod, "ok": bool(mod in REGISTRY)})
        queries.finish_run(run_id, status="done", output_obj={"dry_run": True, "steps": outputs}, error=None)
        return {"mode": "steps", "run_id": run_id, "dry_run": True, "steps": outputs}

    try:
        for i, s in enumerate(steps):
            if not isinstance(s, dict):
                continue
            module_name = s.get("module")
            if not module_name or module_name not in REGISTRY:
                raise ValueError(f"unknown module: {module_name}")

            step_topic = s.get("topic") or topic
            merged = {}
            merged.update(req.constraints or {})
            if isinstance(s.get("constraints"), dict):
                merged.update(s.get("constraints") or {})

            step_id = queries.create_run_step(
                run_id=run_id,
                step_index=i,
                step_type="module",
                module=module_name,
                input_obj={"topic": step_topic, "constraints": merged},
            )

            m = REGISTRY[module_name]
            res = m.generate(step_topic, merged)
            chk = validate_artifacts(res.artifact_paths)
            if not chk.ok:
                raise ValueError("Artifact validation failed: " + "; ".join(chk.problems[:10]))
            cg = run_code_gate(res.artifact_paths)
            out = {
                "step": i,
                "module": module_name,
                "topic": step_topic,
                "artifact_paths": res.artifact_paths,
                "metadata": res.metadata,
                "validation": chk.__dict__,
                "code_gate": cg.__dict__,
            }
            outputs.append(out)
            queries.finish_run_step(step_id, status="done", output_obj=out, error=None)

        queries.finish_run(run_id, status="done", output_obj={"steps": outputs}, error=None)
        if req.session_id is not None:
            append_note(int(req.session_id), "director", "Executed explicit step plan", meta={"run_id": run_id})
        return {"mode": "steps", "run_id": run_id, "steps": outputs}
    except Exception as e:
        queries.finish_run(run_id, status="error", output_obj={"steps": outputs}, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


class AuditReq(BaseModel):
    run_id: int


@router.post("/audit", dependencies=[Depends(require_api_key)])
def audit(req: AuditReq):
    """Summarize validations and code gates for a run."""
    try:
        r = queries.get_run(int(req.run_id))
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    steps = r.get("steps") or []
    summary = {
        "run_id": int(req.run_id),
        "status": r.get("status"),
        "steps_total": len(steps),
        "steps_ok": 0,
        "steps_error": 0,
        "problems": [],
    }
    for s in steps:
        st = (s.get("status") or "").lower()
        if st == "done":
            summary["steps_ok"] += 1
        elif st == "error":
            summary["steps_error"] += 1
            if s.get("error"):
                summary["problems"].append({"step": s.get("step_index"), "module": s.get("module"), "error": s.get("error")})

    return {"run": r, "summary": summary}


class MemoryNoteReq(BaseModel):
    text: str
    meta: Dict[str, Any] = {}


@router.get("/sessions/{session_id}/agents/{agent}", dependencies=[Depends(require_api_key)])
def get_agent_memory(session_id: int, agent: str):
    return mem_load(int(session_id), agent)


@router.post("/sessions/{session_id}/agents/{agent}/note", dependencies=[Depends(require_api_key)])
def add_agent_note(session_id: int, agent: str, req: MemoryNoteReq):
    return append_note(int(session_id), agent, req.text, meta=req.meta)


@router.post("/sessions/{session_id}/agents/{agent}/state", dependencies=[Depends(require_api_key)])
def set_agent_state(session_id: int, agent: str, state: Dict[str, Any]):
    return set_state(int(session_id), agent, state)


@router.post("/sessions/{session_id}/agents/{agent}/reset", dependencies=[Depends(require_api_key)])
def reset_agent(session_id: int, agent: str):
    mem_reset(int(session_id), agent)
    return {"ok": True}
