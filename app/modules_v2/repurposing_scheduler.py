from __future__ import annotations
from typing import Any
import time
from .base import ModuleResult
from .utils import ensure_dir, write_text, write_json, now_iso, slugify
from .. import db

DERIVATIVE_MODULES = ["newsletter_excerpt", "youtube_script", "social_posts", "lead_magnet_snippet"]

class RepurposingScheduler:
    """Connect repurposing outputs to the worker queue with a Fibonacci cadence.

    By default this ONLY writes a schedule (no enqueuing). Set constraints:
    - enqueue: true
    """
    name = "repurposing_scheduler"

    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        out_dir = f"{run_folder}/artifacts/{self.name}"
        ensure_dir(out_dir)

        start_days = int(constraints.get("start_in_days") or 0)
        cadence = constraints.get("cadence_days") or [1, 2, 3, 5, 8]
        if isinstance(cadence, int):
            cadence = [cadence]
        cadence = [int(x) for x in cadence][:9]
        enqueue = bool(constraints.get("enqueue", False))

        now = int(time.time())
        tasks = []
        for i, mod in enumerate(DERIVATIVE_MODULES):
            day = cadence[i % len(cadence)]
            run_after = now + int((start_days + day) * 86400)
            child_sku = f"{sku}-{slugify(mod)[:8]}-{i+1:02d}"
            if enqueue:
                db.enqueue_task(
                    sku=child_sku,
                    topic=f"{topic} — Repurpose: {mod}",
                    tier=tier,
                    price_cents=0,
                    platforms=platforms,
                    constraints={"modules": [mod], "parent_sku": sku, "job": "repurpose", "repurpose_module": mod},
                    run_after=run_after,
                )
            tasks.append({"module": mod, "child_sku": child_sku, "run_after": run_after, "enqueued": enqueue})

        schedule_md = [f"# Repurposing Scheduler — {topic}", ""]
        schedule_md.append("This schedules derivative content builds on a Fibonacci cadence.")
        schedule_md.append(f"Enqueue to worker queue: {'YES' if enqueue else 'NO (plan only)'}")
        schedule_md.append("")
        schedule_md.append("## Tasks")
        for t in tasks:
            schedule_md.append(f"- {t['module']} → {t['child_sku']} on {time.strftime('%Y-%m-%d', time.localtime(t['run_after']))}")

        schedule_path = f"{out_dir}/REPURPOSE_SCHEDULE.md"
        write_text(schedule_path, "\n".join(schedule_md))
        json_path = f"{out_dir}/repurpose_schedule.json"
        write_json(json_path, {"generated_at": now_iso(), "parent_sku": sku, "tasks": tasks})

        return ModuleResult(name=self.name, artifacts=[schedule_path, json_path], summary={"tasks": len(tasks), "enqueued": int(enqueue)})
