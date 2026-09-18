from __future__ import annotations
from typing import Dict, Any
import datetime, time

from app.db import queries
from app.flywheel.builder import build_offer
from app.flywheel.runctx import RunContext
from app.modules import REGISTRY
from app.db.queries import log_audit
from app.factory.factory import run_next as factory_run_next
from app.security.sandbox import validate_artifacts

def _now_iso() -> str:
    return datetime.datetime.utcnow().isoformat()

def _safe_finish_run(run_id: int | None, status: str, output: Dict[str, Any] | None = None, error: str | None = None) -> None:
    if not run_id:
        return
    try:
        queries.finish_run(int(run_id), status=status, output_obj=output or {}, error=error)
    except Exception:
        pass

def run_due(max_tasks: int = 3) -> Dict[str, Any]:
    now = _now_iso()
    due = queries.fetch_due_tasks(now, limit=max_tasks)
    results = []

    for t in due:
        tid = int(t["task_id"])
        payload = t.get("payload") or {}
        module = (t.get("module") or "").strip()
        task_type = (t.get("task_type") or "").strip()
        run_id = t.get("run_id") or payload.get("run_id")
        run_ctx = RunContext(run_id=int(run_id), actor="system") if run_id else None

        try:
            queries.set_task_status(tid, "running", last_result={"note": "started", "run_id": run_id})

            if module == "factory" and task_type == "build_queue_item":
                r = factory_run_next()
                queries.set_task_status(tid, "done", last_result=r)
                results.append({"task_id": tid, "ok": True, "result": r})
                log_audit("system", "task_done", "task", str(tid), {"module": module, "task_type": task_type, "result": r})
                continue

            if task_type == "build_offer":
                r = build_offer(
                    topic=payload["topic"],
                    modules=payload.get("modules") or [],
                    constraints_by_module=payload.get("constraints_by_module") or {},
                    name=payload.get("name"),
                    description=payload.get("description"),
                    price_cents=int(payload.get("price_cents") or 2900),
                    tier=str(payload.get("tier") or "core"),
                    tier_rules_path=payload.get("tier_rules_path"),
                    run_ctx=run_ctx,
                )
                out = {"product_id": r.product_id, "sku": r.sku, "version": r.version, "bundle_zip": r.bundle_zip, "gumroad_dir": r.gumroad_dir}
                queries.set_task_status(tid, "done", last_result=out)
                results.append({"task_id": tid, "ok": True, "result": out})
                log_audit("system", "task_done", "task", str(tid), {"module": module, "task_type": task_type, "result": out})
                _safe_finish_run(run_id, "done", out, None)
                continue

            # default: run a module generation task
            if module in REGISTRY:
                m = REGISTRY[module]
                step_id = None
                if run_id:
                    step_id = queries.create_run_step(run_id=int(run_id), step_index=0, step_type="module", module=module, input_obj=payload)

                r = m.generate(payload.get("topic",""), payload.get("constraints") or {})
                chk = validate_artifacts(r.artifact_paths)
                if not chk.ok:
                    raise ValueError("Artifact validation failed: " + "; ".join(chk.problems[:10]))

                out = {"artifact_paths": r.artifact_paths, "metadata": r.metadata, "validation": chk.__dict__}
                queries.set_task_status(tid, "done", last_result=out)
                results.append({"task_id": tid, "ok": True, "result": out})
                log_audit("system", "task_done", "task", str(tid), {"module": module, "task_type": task_type, "result": out})

                if step_id:
                    queries.finish_run_step(step_id, status="done", output_obj=out, error=None)
                _safe_finish_run(run_id, "done", out, None)
                continue

            queries.set_task_status(tid, "error", last_result={"error": "unknown task"})
            results.append({"task_id": tid, "ok": False, "error": "unknown task"})
            log_audit("system", "task_error", "task", str(tid), {"module": module, "task_type": task_type, "error": "unknown task"})
            _safe_finish_run(run_id, "error", {}, "unknown task")

        except Exception as e:
            err = str(e)
            queries.set_task_status(tid, "error", last_result={"error": err})
            results.append({"task_id": tid, "ok": False, "error": err})
            log_audit("system", "task_error", "task", str(tid), {"module": module, "task_type": task_type, "error": err})
            _safe_finish_run(run_id, "error", {}, err)
    return {"ok": True, "ran": len(results), "results": results}

def run_loop(poll_seconds: int = 15, batch: int = 3) -> None:
    print(f"Task worker running. poll_seconds={poll_seconds} batch={batch}")
    while True:
        res = run_due(max_tasks=batch)
        if res.get("ran", 0) == 0:
            time.sleep(poll_seconds)
        else:
            time.sleep(2)
