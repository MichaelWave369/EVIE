from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Protocol

@dataclass
class ModuleResult:
    artifact_paths: List[str]
    metadata: Dict[str, Any]

class IncomeModule(Protocol):
    name: str
    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult: ...


class BaseModule:
    """Small helper base class (optional).

    Many modules simply implement `generate(topic, constraints)` and return ModuleResult.
    This base class offers a consistent local artifact root helper.
    """

    name: str = "base"

    def artifact_root(self, topic_slug: str, namespace: str) -> "Path":
        from pathlib import Path
        from app.settings import settings
        root = Path(settings.data_dir) / "artifacts" / namespace / topic_slug
        root.mkdir(parents=True, exist_ok=True)
        return root
