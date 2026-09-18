from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def _default_payload() -> dict:
    return {
        "preferred_assets": {},
        "history": [],
        "updated_at": datetime.utcnow().isoformat(),
    }


def load_state(state_path: str | Path) -> dict:
    p = Path(state_path)
    if not p.exists():
        return _default_payload()
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return _default_payload()
        payload.setdefault("preferred_assets", {})
        payload.setdefault("history", [])
        payload.setdefault("updated_at", datetime.utcnow().isoformat())
        return payload
    except Exception:
        return _default_payload()


def set_preferred_asset(state_path: str | Path, *, category: str, asset_path: str, source: str, note: str = "") -> dict:
    p = Path(state_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    state = load_state(p)
    state["preferred_assets"][category] = {
        "asset_path": asset_path,
        "source": source,
        "note": note,
        "updated_at": datetime.utcnow().isoformat(),
    }
    state["history"].append(
        {
            "category": category,
            "asset_path": asset_path,
            "source": source,
            "note": note,
            "at": datetime.utcnow().isoformat(),
        }
    )
    state["updated_at"] = datetime.utcnow().isoformat()
    p.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return state
