from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.settings import settings
from app.workflows.runner import list_workflows
from app.rag.llm import LLM


@dataclass
class SwarmPlan:
    """A runnable plan.

    Either chooses a workflow name, or provides an explicit list of module steps.
    """

    goal: str
    topic: str
    workflow: Optional[str]
    steps: List[Dict[str, Any]]
    confidence: float = 0.5
    director_backend: str = "heuristic"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "topic": self.topic,
            "workflow": self.workflow,
            "steps": self.steps,
            "confidence": self.confidence,
            "director_backend": self.director_backend,
        }


def _heuristic_pick(goal: str) -> str:
    g = (goal or "").lower()
    # Lightweight intent routing
    if any(k in g for k in ["youtube", "video", "channel", "thumbnail", "script"]):
        return "youtube_flywheel"
    if any(k in g for k in ["seo", "blog", "pseo", "site", "sitemap", "keywords"]):
        return "pseo_site_compiler"
    if any(k in g for k in ["offer", "sales", "landing", "storefront", "gumroad", "checkout"]):
        return "offer_to_storefront"
    # default
    return "offer_to_storefront"


def _llm_plan(goal: str, topic: str) -> Optional[SwarmPlan]:
    """Ask the local LLM to choose the best workflow.

    We keep this *very* small to reduce brittleness: the model only needs to
    return a JSON object with {workflow, confidence, notes?}. If it fails, we
    fall back to heuristics.
    """
    try:
        wf = list_workflows()
        wf_lines = [f"- {w['name']}: {w.get('description','')}" for w in wf]
        sys = (
            "You are EVIE Swarm Director. Choose the best workflow for the user's goal. "
            "Return ONLY valid JSON with keys: workflow (string), confidence (0..1), steps (optional list)."
        )
        user = (
            f"Goal: {goal}\n"
            f"Topic: {topic}\n\n"
            "Available workflows:\n" + "\n".join(wf_lines)
        )
        llm = LLM.from_settings()
        out = llm.chat([
            {"role": "system", "content": sys},
            {"role": "user", "content": user},
        ])
        data = json.loads(out)
        workflow = data.get("workflow")
        if not isinstance(workflow, str) or not workflow:
            return None
        conf = float(data.get("confidence") or 0.6)
        steps = data.get("steps")
        if not isinstance(steps, list):
            steps = []
        return SwarmPlan(goal=goal, topic=topic, workflow=workflow, steps=steps, confidence=conf, director_backend="ollama")
    except Exception:
        return None


def make_plan(
    *,
    goal: str,
    topic: Optional[str] = None,
    constraints: Optional[Dict[str, Any]] = None,
    prefer_backend: Optional[str] = None,
) -> SwarmPlan:
    """Create a runnable plan.

    If EV_SWARM_DIRECTOR_BACKEND=ollama (and EV_LLM_BACKEND=ollama), EVIE will
    try to use the local LLM for workflow selection. Otherwise it uses a
    deterministic heuristic router.
    """

    topic = (topic or goal or "Untitled").strip()
    backend = (prefer_backend or getattr(settings, "swarm_director_backend", "heuristic")).lower().strip()

    if backend == "ollama" and settings.llm_backend.lower().strip() == "ollama":
        plan = _llm_plan(goal, topic)
        if plan:
            # merge constraints into step constraints if steps provided (optional)
            if constraints and plan.steps:
                for s in plan.steps:
                    if isinstance(s, dict):
                        c = s.get("constraints")
                        merged = {}
                        merged.update(constraints)
                        if isinstance(c, dict):
                            merged.update(c)
                        s["constraints"] = merged
            return plan

    # Heuristic routing
    wf_name = _heuristic_pick(goal)
    return SwarmPlan(goal=goal, topic=topic, workflow=wf_name, steps=[], confidence=0.55, director_backend="heuristic")
