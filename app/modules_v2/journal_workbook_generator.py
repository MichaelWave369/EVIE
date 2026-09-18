from __future__ import annotations
from typing import Any
import os
from .base import ModuleResult
from .utils import ensure_dir, write_text, write_json, now_iso, three_six_nine_sections

class JournalWorkbookGenerator:
    """Printable workbook/journal generator. Outputs Markdown + optional PDF."""
    name = "journal_workbook_generator"

    def _try_pdf(self, pdf_path: str, title: str, sections: list[str]):
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
        except Exception:
            return False
        c = canvas.Canvas(pdf_path, pagesize=letter)
        width, height = letter
        y = height - 72
        c.setFont("Helvetica-Bold", 16)
        c.drawString(72, y, title)
        y -= 36
        c.setFont("Helvetica", 11)
        for sec in sections:
            if y < 120:
                c.showPage()
                y = height - 72
                c.setFont("Helvetica", 11)
            c.drawString(72, y, sec)
            y -= 18
            # write blank lines
            for _ in range(4):
                if y < 120:
                    c.showPage()
                    y = height - 72
                    c.setFont("Helvetica", 11)
                c.line(72, y, width-72, y)
                y -= 18
            y -= 10
        c.save()
        return True

    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        out_dir = f"{run_folder}/artifacts/{self.name}"
        ensure_dir(out_dir)

        bullets3 = ["Reflect", "Track", "Transform"]
        bullets6 = [
            "Daily check-in page (3 prompts)",
            "Weekly review page (6 prompts)",
            "Monthly reset page (9 prompts)",
            "Habit/goal tracker",
            "Notes pages",
            "Export-ready PDF/print format"
        ]
        bullets9 = [
            "Keep prompts short and kind",
            "No medical claims",
            "Make pages repeatable",
            "Use 369 checklists",
            "Use Φ pacing (short first)",
            "Use Fib cadence (1/2/3/5/8)",
            "Add space to write",
            "Add checkboxes",
            "Add a recap page"
        ]
        workbook = three_six_nine_sections(f"{topic} — Journal/Workbook (Printable)", bullets3, bullets6, bullets9)

        workbook += """\n\n---\n\n## Daily Check-In (3)
1) What matters today?
2) What is one small win?
3) What is one thing to release?

## Weekly Review (6)
1) Best moment
2) Biggest lesson
3) What drained energy
4) What gave energy
5) One improvement
6) Next Fib step (1/2/3/5/8 days)

## Monthly Reset (9)
1) Theme
2) Goals
3) Constraints
4) Support
5) Boundaries
6) System upgrade
7) Celebrate
8) Simplify
9) Commit
\n\n## Trackers
- Habit tracker (21 days)
- Mood/energy tracker (1–9)
\n\n## Notes pages
(Repeat as needed.)
"""

        md_path = f"{out_dir}/WORKBOOK.md"
        write_text(md_path, workbook)

        pdf_path = f"{out_dir}/WORKBOOK.pdf"
        made_pdf = self._try_pdf(pdf_path, f"{topic} — Workbook", [
            "Daily Check-In: What matters today?",
            "Daily Check-In: One small win?",
            "Daily Check-In: One thing to release?",
            "Weekly Review: Biggest lesson?",
            "Monthly Reset: Theme + goals?",
        ])
        artifacts = [md_path]
        if made_pdf and os.path.exists(pdf_path):
            artifacts.append(pdf_path)

        write_json(f"{out_dir}/workbook.json", {"sku": sku, "topic": topic, "generated_at": now_iso(), "pdf": bool(made_pdf)})
        artifacts.append(f"{out_dir}/workbook.json")
        return ModuleResult(name=self.name, artifacts=artifacts, summary={"pdf": bool(made_pdf)})
