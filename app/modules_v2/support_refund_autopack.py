from __future__ import annotations
from typing import Any
from .base import ModuleResult
from .utils import write_text, ensure_dir

class SupportRefundAutopack:
    name = "support_refund_autopack"
    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        out_dir = f"{run_folder}/artifacts/{self.name}"
        ensure_dir(out_dir)
        write_text(f"{out_dir}/REFUND_POLICY.md", "# Refund Policy (Template)\n- Digital products: case-by-case\n- No guarantees of outcomes\n")
        write_text(f"{out_dir}/TROUBLESHOOTING_FLOW.md", "# Troubleshooting Flow (6)\n1) Confirm download\n2) Confirm unzip\n3) Confirm file opens\n4) Try alternate app\n5) Re-download\n6) Contact support\n")
        write_text(f"{out_dir}/KNOWN_ISSUES.md", "# Known Issues\n- Placeholder\n")
        return ModuleResult(name=self.name, artifacts=[f"{out_dir}/REFUND_POLICY.md", f"{out_dir}/TROUBLESHOOTING_FLOW.md", f"{out_dir}/KNOWN_ISSUES.md"], summary={"ok": True})
