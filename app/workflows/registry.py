from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from app.settings import settings


def registry_path() -> Path:
    p = Path(getattr(settings, "workflow_registry_path", "./configs/workflows.json"))
    return p


def load_registry() -> Dict[str, Any]:
    p = registry_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_registry(reg: Dict[str, Any]) -> None:
    p = registry_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
