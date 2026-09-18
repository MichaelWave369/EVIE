from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.settings import settings


def _root() -> Path:
    """Agent memory root directory (local-only)."""
    d = Path(getattr(settings, "agent_memory_dir", settings.data_dir / "agent_memory"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _mem_path(session_id: int, agent: str) -> Path:
    safe_agent = "".join(ch for ch in (agent or "agent") if ch.isalnum() or ch in "-_" )[:40]
    d = _root() / str(int(session_id))
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{safe_agent}.json"


def load(session_id: int, agent: str) -> Dict[str, Any]:
    p = _mem_path(session_id, agent)
    if not p.exists():
        return {"agent": agent, "session_id": int(session_id), "notes": [], "state": {}}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"agent": agent, "session_id": int(session_id), "notes": [], "state": {}}


def save(session_id: int, agent: str, obj: Dict[str, Any]) -> None:
    p = _mem_path(session_id, agent)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def append_note(session_id: int, agent: str, text: str, *, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    obj = load(session_id, agent)
    notes: List[Dict[str, Any]] = obj.get("notes") if isinstance(obj.get("notes"), list) else []
    notes.append({"text": (text or "").strip(), "meta": meta or {}})
    obj["notes"] = notes[-200:]  # cap
    save(session_id, agent, obj)
    return obj


def set_state(session_id: int, agent: str, state: Dict[str, Any]) -> Dict[str, Any]:
    obj = load(session_id, agent)
    obj["state"] = state or {}
    save(session_id, agent, obj)
    return obj


def reset(session_id: int, agent: str) -> None:
    p = _mem_path(session_id, agent)
    try:
        if p.exists():
            p.unlink()
    except Exception:
        pass
