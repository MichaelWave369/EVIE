from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Optional
import datetime
import json
import csv

from app.modules.base import ModuleResult
from app.rag.llm import LLM
from app.settings import settings
from app.export.packager import write_text


def _read_inbox_csv(path: str, max_rows: int = 500) -> List[Dict[str, str]]:
    p = Path(path)
    if not p.exists():
        return []
    rows: List[Dict[str, str]] = []
    with p.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)
        for i, r in enumerate(reader):
            if i >= max_rows:
                break
            rows.append({k: (v or "") for k, v in r.items()})
    return rows


class InboxFAQBuilderModule:
    """Support inbox → FAQ + macros + product improvements.

    Inputs (constraints):
    - inbox_csv_path: path to a local CSV export (recommended)
      columns may include: subject, body, message, question, category, timestamp
    - messages: list[str] (fallback)
    - tone: "friendly" | "formal" | "direct"

    Outputs:
    - faq.md
    - support_macros.md
    - product_updates.md (suggested fixes + changelog entry)
    """

    name = "inbox_faq_builder"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        llm = LLM.from_settings()
        tone = constraints.get("tone", "friendly")

        inbox_csv_path = constraints.get("inbox_csv_path")
        messages = constraints.get("messages") or []
        inbox_rows = _read_inbox_csv(inbox_csv_path) if isinstance(inbox_csv_path, str) else []

        # Build a compact text sample for the LLM
        sample_lines: List[str] = []
        if inbox_rows:
            keys = list(inbox_rows[0].keys())[:8]
            for r in inbox_rows[:50]:
                bits = []
                for k in keys:
                    v = (r.get(k) or "").strip().replace("\n", " ")
                    if v:
                        bits.append(f"{k}={v[:140]}")
                if bits:
                    sample_lines.append(" | ".join(bits))
        elif isinstance(messages, list):
            for m in messages[:50]:
                m = str(m).strip().replace("\n", " ")
                if m:
                    sample_lines.append(m[:220])

        sample = "\n".join([f"- {x}" for x in sample_lines]) if sample_lines else "- (no inbox provided yet)"

        prompt = f"""You are a support + product-improvement assistant.

Topic/product: {topic}
Tone: {tone}

Here are customer/support messages (sample):
{sample}

Create outputs that are 369 aligned:
- 3 most common questions (top issues)
- 6 FAQ entries
- 9 support macros (short canned replies)
Also produce:
- A 'Product Updates' section with 1/2/3/5/8-day fix plan
- A changelog snippet (markdown) for the next release
- A safe disclaimers note (no guarantees; user responsibility; privacy)

Return as JSON with keys:
faq_md, macros_md, product_updates_md, changelog_snippet_md
"""

        data = None
        raw = None
        if llm.backend != "none":
            raw = llm.chat([{"role": "user", "content": prompt}])
            try:
                data = json.loads(raw)
            except Exception:
                data = None

        if not isinstance(data, dict):
            # Fallback templates
            data = {
                "faq_md": f"# FAQ — {topic}\n\n## Top 3 questions\n1. What is this?\n2. How do I use it?\n3. What do I get?\n\n## FAQs (6)\n- Q: ...\n  A: ...\n",
                "macros_md": f"# Support Macros — {topic}\n\n(Write 9 canned replies here: refunds, install, access, scope, updates, etc.)\n",
                "product_updates_md": f"# Product Updates — {topic}\n\n## Fix plan (1/2/3/5/8 days)\n- Day 1: ...\n- Day 2: ...\n- Day 3: ...\n- Day 5: ...\n- Day 8: ...\n",
                "changelog_snippet_md": f"- Support/FAQ refresh (auto-generated)\n- Added clearer onboarding + troubleshooting\n- 369 • Φ • Fib alignment maintained\n",
            }
            if raw:
                data["llm_raw"] = raw

        out_dir = Path(settings.data_dir) / "artifacts" / "support_inbox"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        faq_path = out_dir / f"faq__{ts}.md"
        macros_path = out_dir / f"macros__{ts}.md"
        updates_path = out_dir / f"product_updates__{ts}.md"
        snippet_path = out_dir / f"changelog_snippet__{ts}.md"
        json_path = out_dir / f"inbox_summary__{ts}.json"

        write_text(faq_path, str(data.get("faq_md", "")))
        write_text(macros_path, str(data.get("macros_md", "")))
        write_text(updates_path, str(data.get("product_updates_md", "")))
        write_text(snippet_path, str(data.get("changelog_snippet_md", "")))
        write_text(json_path, json.dumps({"topic": topic, "tone": tone, "inbox_csv_path": inbox_csv_path, "sample_count": len(sample_lines)}, indent=2))

        return ModuleResult(
            artifact_paths=[str(faq_path), str(macros_path), str(updates_path), str(snippet_path), str(json_path)],
            metadata={"topic": topic, "module": self.name, "tone": tone, "sample_count": len(sample_lines)},
        )
