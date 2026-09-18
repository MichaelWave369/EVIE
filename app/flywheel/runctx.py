from __future__ import annotations

import datetime, json
from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.db import queries


def _now() -> str:
    return datetime.datetime.utcnow().isoformat()


@dataclass
class RunContext:
    run_id: int
    actor: str = "system"

    def step_start(self, step_index: int, step_type: str, module: str | None, input_obj: Dict[str, Any]) -> int:
        return queries.create_run_step(
            run_id=self.run_id,
            step_index=step_index,
            step_type=step_type,
            module=module,
            input_obj=input_obj,
        )

    def step_done(self, step_id: int, output_obj: Dict[str, Any]) -> None:
        queries.finish_run_step(step_id, status="done", output_obj=output_obj, error=None)

    def step_error(self, step_id: int, error: str) -> None:
        queries.finish_run_step(step_id, status="error", output_obj={}, error=error)

    def done(self, output_obj: Dict[str, Any]) -> None:
        queries.finish_run(self.run_id, status="done", output_obj=output_obj, error=None)

    def error(self, error: str) -> None:
        queries.finish_run(self.run_id, status="error", output_obj={}, error=error)
