from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.modules import REGISTRY
from app.security.sandbox import validate_artifacts
from app.qa.code_safety_gate import run_code_gate
from app.db import queries
from app.workflows.registry import load_registry


def list_workflows() -> List[Dict[str, Any]]:
    reg = load_registry()
    out = []
    for name, spec in sorted(reg.items()):
        if not isinstance(spec, dict):
            continue
        out.append({
            "name": name,
            "description": spec.get("description", ""),
            "steps": spec.get("steps", []),
            "tags": spec.get("tags", []),
            "input_schema": spec.get("input_schema", {}),
            "example_constraints": spec.get("example_constraints", {}),
            "notes": spec.get("notes", ""),
        })
    return out


def run_workflow(
    name: str,
    *,
    topic: str,
    constraints: Dict[str, Any] | None = None,
    actor: str = "api",
    campaign_id: Optional[int] = None,
    session_id: Optional[int] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    reg = load_registry()
    wf = reg.get(name)
    if not isinstance(wf, dict):
        raise KeyError(f"workflow '{name}' not found")

    steps = wf.get("steps") or []
    if not isinstance(steps, list) or not steps:
        raise ValueError("workflow has no steps")

    # Create run record (observability)
    run_id = queries.create_run(
        run_type="workflow",
        module=name,
        topic=topic,
        input_obj={"topic": topic, "constraints": constraints or {}, "workflow": wf},
        actor=actor,
        campaign_id=campaign_id,
        session_id=session_id,
    )

    outputs: List[Dict[str, Any]] = []
    collected_artifacts: List[str] = []
    module_artifacts: Dict[str, List[str]] = {}
    module_metadata: Dict[str, Dict[str, Any]] = {}

    # In dry_run mode, only validate step availability
    if dry_run:
        for i, s in enumerate(steps):
            mod = (s or {}).get("module")
            wf_name = (s or {}).get("workflow")
            if wf_name:
                ok = bool(load_registry().get(wf_name))
                outputs.append({"step": i, "workflow": wf_name, "ok": ok})
            else:
                ok = bool(mod in REGISTRY)
                outputs.append({"step": i, "module": mod, "ok": ok})
        queries.finish_run(run_id, status="done", output_obj={"dry_run": True, "steps": outputs}, error=None)
        return {"run_id": run_id, "dry_run": True, "steps": outputs}

    for i, s in enumerate(steps):
        if not isinstance(s, dict):
            continue
        module_name = s.get("module")
        nested_workflow = s.get("workflow")
        if nested_workflow:
            module_name = f"workflow:{nested_workflow}"
        if not nested_workflow and (not module_name or module_name not in REGISTRY):
            raise ValueError(f"unknown module in workflow: {module_name}")

        when_constraint = s.get("when_constraint")
        if when_constraint and not bool((constraints or {}).get(str(when_constraint))):
            outputs.append({
                "step": i,
                "module": module_name,
                "status": "skipped",
                "reason": f"Constraint flag '{when_constraint}' not enabled",
            })
            continue

        step_topic = s.get("topic") or topic
        # merge constraints: workflow step constraints override request constraints
        merged: Dict[str, Any] = {}
        if isinstance(constraints, dict):
            merged.update(constraints)
        if isinstance(s.get("constraints"), dict):
            merged.update(s.get("constraints") or {})
        if collected_artifacts and "artifact_paths" not in merged:
            merged["artifact_paths"] = list(collected_artifacts)
        if module_metadata and "workflow_step_metadata" not in merged:
            merged["workflow_step_metadata"] = dict(module_metadata)

        # Lightweight handoff conventions for media workflows.
        if module_name == "audio_generator" and "script_path" not in merged:
            script_candidates = module_artifacts.get("podcast_script_generator", [])
            script = next((p for p in script_candidates if str(p).lower().endswith(".md")), "")
            if script:
                merged["script_path"] = script
        if module_name == "video_generator":
            if "audio_path" not in merged:
                audio_candidates = module_artifacts.get("audio_generator", [])
                audio = next((p for p in audio_candidates if str(p).lower().endswith(".mp3")), "")
                if audio:
                    merged["audio_path"] = audio
            if "slides" not in merged:
                slide_candidates: List[str] = []
                for modn in ("infographic_generator", "presentation_generator"):
                    slide_candidates.extend(module_artifacts.get(modn, []))
                png_slides = [p for p in slide_candidates if str(p).lower().endswith(".png")]
                if png_slides:
                    merged["slides"] = png_slides
        if module_name == "youtube_publisher" and "video_path" not in merged:
            vid_candidates = module_artifacts.get("video_generator", [])
            vid = next((p for p in vid_candidates if str(p).lower().endswith(".mp4")), "")
            if vid:
                merged["video_path"] = vid

        step_id = queries.create_run_step(
            run_id=run_id,
            step_index=i,
            step_type="module",
            module=module_name,
            input_obj={"topic": step_topic, "constraints": merged},
        )

        try:
            if nested_workflow:
                if nested_workflow == name:
                    raise ValueError(f"workflow '{name}' cannot include itself")
                child = run_workflow(
                    nested_workflow,
                    topic=step_topic,
                    constraints=merged,
                    actor=actor,
                    campaign_id=campaign_id,
                    session_id=session_id,
                    dry_run=False,
                )
                child_steps = child.get("steps") or []
                child_artifacts: List[str] = []
                for cs in child_steps:
                    child_artifacts.extend((cs or {}).get("artifact_paths") or [])
                    cm = (cs or {}).get("module")
                    cmeta = (cs or {}).get("metadata")
                    if cm and isinstance(cmeta, dict):
                        module_metadata[cm] = dict(cmeta)
                out = {
                    "step": i,
                    "module": module_name,
                    "status": child.get("status", "done"),
                    "topic": step_topic,
                    "artifact_paths": child_artifacts,
                    "metadata": {
                        "workflow": nested_workflow,
                        "child_run_id": child.get("run_id"),
                        "child_status": child.get("status", "done"),
                        "child_steps": child_steps,
                    },
                    "validation": {"ok": True, "checked": len(child_artifacts), "total_bytes": 0, "problems": []},
                    "code_gate": {"ok": True},
                }
                outputs.append(out)
                if child_artifacts:
                    collected_artifacts.extend(child_artifacts)
                    module_artifacts[module_name] = list(child_artifacts)
                module_metadata[nested_workflow] = dict(out["metadata"])
                queries.finish_run_step(step_id, status="done", output_obj=out, error=None)
                continue

            m = REGISTRY[module_name]
            res = m.generate(step_topic, merged)
            md = res.metadata or {}
            step_error = md.get("error") or (md.get("v2_summary") or {}).get("error")
            is_optional = bool(s.get("optional"))
            if step_error and not res.artifact_paths and not is_optional:
                raise ValueError(str(step_error))

            chk = validate_artifacts(res.artifact_paths)
            if not chk.ok:
                raise ValueError("Artifact validation failed: " + "; ".join(chk.problems[:10]))

            code_gate = run_code_gate(res.artifact_paths)
            if not code_gate.ok:
                raise ValueError("Code safety gate failed")

            out = {
                "step": i,
                "module": module_name,
                "status": "partial" if (is_optional and step_error) else "done",
                "topic": step_topic,
                "artifact_paths": res.artifact_paths,
                "metadata": res.metadata,
                "validation": chk.__dict__,
                "code_gate": code_gate.__dict__,
            }
            outputs.append(out)
            if res.artifact_paths:
                collected_artifacts.extend(res.artifact_paths)
                module_artifacts[module_name] = list(res.artifact_paths)
            if isinstance(res.metadata, dict):
                module_metadata[module_name] = dict(res.metadata)
            queries.finish_run_step(step_id, status="done", output_obj=out, error=None)
        except Exception as e:
            if bool(s.get("optional")):
                out = {
                    "step": i,
                    "module": module_name,
                    "status": "partial",
                    "topic": step_topic,
                    "artifact_paths": [],
                    "metadata": {"error": str(e), "optional": True},
                }
                outputs.append(out)
                queries.finish_run_step(step_id, status="done", output_obj=out, error=None)
                continue
            queries.finish_run_step(step_id, status="error", output_obj={}, error=str(e))
            queries.finish_run(run_id, status="error", output_obj={"steps": outputs}, error=str(e))
            raise

    has_partial = any((s or {}).get("status") == "partial" for s in outputs)
    final_status = "partial" if has_partial else "done"
    queries.finish_run(run_id, status=final_status, output_obj={"workflow": name, "steps": outputs}, error=None)
    return {"run_id": run_id, "workflow": name, "status": final_status, "steps": outputs}
