from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List
import datetime
import json

from app.modules.base import ModuleResult
from app.settings import settings
from app.flywheel.slug import slugify
from app.export.packager import write_text
from app.rag.llm import LLM


def _fib(n: int) -> List[int]:
    if n <= 0:
        return []
    seq = [1, 2]
    while len(seq) < n:
        seq.append(seq[-1] + seq[-2])
    return seq[:n]


def _issue_template(topic: str, week: int, cadence_day: int) -> str:
    return (
        f"# Issue {week:02d} — {topic}\n\n"
        f"**Cadence marker (Fib):** Day {cadence_day}\n\n"
        "## 3-line opener\n"
        "- What we’re focusing on\n"
        "- Why it matters now\n"
        "- The smallest next step\n\n"
        "## 6-minute lesson\n"
        "1) Context\n2) Principle\n3) Example\n4) Common failure\n5) Fix\n6) Next action\n\n"
        "## 9-step action ladder\n"
        "1. …\n2. …\n3. …\n4. …\n5. …\n6. …\n7. …\n8. …\n9. …\n\n"
        "## Repurpose Pack\n"
        "- **Newsletter (long):** draft below\n"
        "- **Social (3):** 3 short posts\n"
        "- **Short video (5 bullets):** hook + beats\n"
        "- **Email (8 lines):** simple follow-up\n\n"
        "Alignment: 369 • Φ • Fib\n"
    )


class MembershipIssueGeneratorModule:
    """Weekly issue drafts + repurpose pack (local-first).

    Produces N issues (default 9) with a 369 structure:
      - 3-line opener
      - 6-minute lesson
      - 9-step action ladder
      - Repurpose pack (newsletter + social + short video + email)

    Uses local LLM if enabled; otherwise outputs structured templates.
    """

    name = "membership_issue_generator"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        key = slugify(topic)
        out_root = Path(settings.data_dir) / "artifacts" / "membership_issues" / key
        out_root.mkdir(parents=True, exist_ok=True)

        weeks = int(constraints.get("weeks") or 9)
        weeks = max(1, min(36, weeks))

        llm = LLM.from_settings()
        fib_days = _fib(weeks)

        artifacts: List[str] = []
        index: List[Dict[str, Any]] = []

        for i in range(1, weeks + 1):
            day = fib_days[i - 1] if i - 1 < len(fib_days) else (fib_days[-1] + i)
            base = _issue_template(topic, i, day)

            # Optional LLM fill
            prompt = (
                f"Fill this membership issue template with concrete content.\n\n"
                f"Topic: {topic}\n"
                f"Week: {i}\n\n"
                "Rules:\n"
                "- Keep structure exactly: 3-line opener, 6-minute lesson, 9-step action ladder, Repurpose Pack.\n"
                "- No hype, no guaranteed results.\n"
                "- Use 369 / Φ / Fib alignment language lightly and tastefully.\n\n"
                "Template:\n"
                f"{base}\n"
            )
            filled = llm.chat([{"role": "user", "content": prompt}])

            issue_path = out_root / f"issue_{i:02d}.md"
            write_text(issue_path, filled if filled.strip() else base)
            artifacts.append(str(issue_path))
            index.append({"week": i, "path": str(issue_path), "fib_day": day})

        manifest = {
            "module": self.name,
            "topic": topic,
            "created_at": datetime.datetime.utcnow().isoformat(),
            "alignment": "369 • Φ • Fib",
            "weeks": weeks,
            "issues": index,
        }
        (out_root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        artifacts.append(str(out_root / "manifest.json"))

        readme = (
            "# Membership Issues Pack\n\n"
            "This folder contains weekly issue drafts for a membership or paid newsletter.\n\n"
            "- issue_XX.md: each issue includes a repurpose pack\n"
            "- manifest.json: structured index\n\n"
            "Tips:\n"
            "- Export each issue into your email platform manually (local-first).\n"
            "- Reuse the repurpose pack for YouTube/Shorts/blog/social.\n\n"
            "Alignment: 369 • Φ • Fib\n"
        )
        write_text(out_root / "README.md", readme)
        artifacts.append(str(out_root / "README.md"))

        return ModuleResult(artifact_paths=artifacts, metadata={"out_root": str(out_root), "weeks": weeks})
