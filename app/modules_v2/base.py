from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Protocol

@dataclass
class ModuleResult:
    name: str
    artifacts: list[str]
    summary: dict[str, Any]

class Module(Protocol):
    name: str
    def generate(
        self,
        *,
        topic: str,
        run_folder: str,
        sku: str,
        tier: str,
        price_cents: int,
        platforms: list[str],
        constraints: dict[str, Any],
    ) -> ModuleResult:
        ...
