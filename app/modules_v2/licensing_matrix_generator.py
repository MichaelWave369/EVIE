from __future__ import annotations
from typing import Any
from .base import ModuleResult
from .utils import write_text, write_json, ensure_dir

class LicensingMatrixGenerator:
    name = "licensing_matrix_generator"
    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        out_dir = f"{run_folder}/artifacts/{self.name}"
        ensure_dir(out_dir)
        write_text(f"{out_dir}/LICENSE_MATRIX.md", f"""# License Matrix — {topic}

## Personal
- Use for yourself
- No resale of raw files

## Commercial
- Use in your business
- No resale of raw files

## Resale / Distribution (Premium)
- You may bundle as part of a larger product
- Keep attribution + no-claims language

> Template only — review for your situation.
""")
        write_json(f"{out_dir}/license_matrix.json", {"sku": sku, "tier": tier, "modes": ["personal","commercial","resale"]})
        return ModuleResult(name=self.name, artifacts=[f"{out_dir}/LICENSE_MATRIX.md", f"{out_dir}/license_matrix.json"], summary={"ok": True})
