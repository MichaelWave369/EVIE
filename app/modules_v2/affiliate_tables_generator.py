from __future__ import annotations
from typing import Any
from .base import ModuleResult
from .utils import write_text, write_json, ensure_dir

class AffiliateTablesGenerator:
    name = "affiliate_tables_generator"
    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        out_dir = f"{run_folder}/artifacts/{self.name}"
        ensure_dir(out_dir)
        items = constraints.get("items") or [f"Tool {i}" for i in range(1,10)]
        table = ["# Comparison Table (9)","", "| Item | Best for | Pros | Cons | Link |", "|---|---|---|---|---|"]
        for it in items[:9]:
            table.append(f"| {it} | ____ | ____ | ____ | [link](#) |")
        write_text(f"{out_dir}/comparison_table.md", "\n".join(table) + "\n\n> Disclosure: affiliate links may earn a commission.")
        write_text(f"{out_dir}/best_for_matrix.md", "# Best-For Matrix (3×3)\n\n| Best for | Pick | Why |\n|---|---|---|\n| Beginners | ____ | ____ |\n| Operators | ____ | ____ |\n| Pros | ____ | ____ |\n")
        write_json(f"{out_dir}/items.json", {"items": items})
        return ModuleResult(name=self.name, artifacts=[f"{out_dir}/comparison_table.md", f"{out_dir}/best_for_matrix.md", f"{out_dir}/items.json"], summary={"items": len(items[:9])})
