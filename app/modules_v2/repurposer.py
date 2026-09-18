from __future__ import annotations
from typing import Any
from .base import ModuleResult
from .utils import ensure_dir, write_text, write_json, now_iso

class Repurposer:
    """Generate derivative content from a core piece (manual/one-shot)."""
    name = "repurposer"

    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        out_dir = f"{run_folder}/artifacts/{self.name}"
        ensure_dir(out_dir)
        core = constraints.get("core_text") or "(paste your core text/chapter here)"
        md = f"""# Repurpose Pack — {topic}

## Core (source)
{core}

---

## Outputs (Fib)
1) Newsletter excerpt
2) YouTube script
3) 3 social posts
5) Lead magnet snippet
8) FAQ objections

Use the dedicated modules (newsletter/youtube/social/lead-magnet) if you want them as separate build tasks.
"""
        path = f"{out_dir}/REPURPOSE_PACK.md"
        write_text(path, md)
        write_json(f"{out_dir}/repurposer.json", {"sku": sku, "topic": topic, "generated_at": now_iso()})
        return ModuleResult(name=self.name, artifacts=[path, f"{out_dir}/repurposer.json"], summary={"ok": True})
