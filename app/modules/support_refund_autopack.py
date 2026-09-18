
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List
import datetime, csv, json

from app.modules.base import ModuleResult
from app.settings import settings
from app.flywheel.slug import slugify
from app.export.packager import write_text
from app.rag.llm import LLM

def _load_inbox(csv_path: Path, max_rows: int = 200) -> List[Dict[str,str]]:
    rows = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for i, r in enumerate(reader):
            if i >= max_rows:
                break
            rows.append({k.strip(): (v or "").strip() for k,v in r.items()})
    return rows

def _fallback(topic: str) -> Dict[str, str]:
    return {
        "macros": f"""# Support Macros (9) — {topic}

1) **Welcome + Clarify**: Thanks for reaching out… can you share (A/B/C)?
2) **Download Help**: Here’s where to find your ZIP and how to unzip…
3) **Install Help**: Here are 3 steps… then 6 checks… then 9 common fixes…
4) **Refund Request**: I can help—before refund, try these quick steps…
5) **License Question**: Personal vs Commercial vs Resale summary…
6) **Bug Report Intake**: OS/version/logs/repro steps…
7) **Feature Request**: Logged—here’s the roadmap cadence (Fib)…
8) **Access / Link Issues**: Reset, re-download, browser tips…
9) **Closeout**: Confirm resolved + ask for 1 sentence feedback.

> Opt-in only. No guarantees. Be kind.\n""",
        "refund": """# Refund Policy (Template)

- **Window:** 7–30 days (choose one)  
- **Digital goods:** refunds offered when files are corrupted, access fails, or the product is materially misrepresented.  
- **Exclusions:** misuse, ignoring instructions, prohibited use.  
- **Process:** contact support with order ID + issue summary.

> Not legal advice. Align with your platform rules.\n""",
        "troubleshooting": """# Troubleshooting Flow (3/6/9)

## 3: Identify
1) What product/SKU?
2) What OS/device?
3) What exact error?

## 6: Fix
1) Re-download
2) Unzip with a different tool
3) Check antivirus quarantine
4) Verify Python/requirements
5) Run the quick test command
6) Send logs

## 9: Escalate
1) Repro steps
2) Screenshots
3) Logs
4) Version info
5) Environment file
6) File listing
7) Time of failure
8) What you expected
9) What happened\n""",
        "known_issues": """# Known Issues (Seed)

- Windows path length issues on unzip (use shorter folder path)
- Missing optional dependencies (OCR/Whisper/LanceDB)
- Ollama not running (start local server)
- API key mismatch (X-API-Key header)
\n"""
    }

class SupportRefundAutoPackModule:
    name = "support_refund_autopack"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        slug = slugify(topic)
        out_dir = settings.data_dir / "artifacts" / "support_refund_autopack" / slug
        out_dir.mkdir(parents=True, exist_ok=True)

        pack = _fallback(topic)

        inbox_path = constraints.get("inbox_csv_path")
        inbox_rows = []
        if inbox_path:
            p = Path(inbox_path)
            if p.exists():
                inbox_rows = _load_inbox(p)

        # Optional LLM improvement using inbox themes
        try:
            llm = LLM.from_settings()
            if llm.backend != "none" and bool(constraints.get("llm_refine", True)):
                themes = ""
                if inbox_rows:
                    sample = "\n".join([str(r)[:240] for r in inbox_rows[:12]])
                    themes = f"Here are sample support messages:\n{sample}\n\n"
                prompt = (
                    f"{themes}Create a support + refund autopack for a digital product about: {topic}. "
                    "Return 4 Markdown documents: SUPPORT_MACROS.md (9 macros), REFUND_POLICY.md, TROUBLESHOOTING_FLOW.md, KNOWN_ISSUES.md. "
                    "Keep 3/6/9 structure and avoid risky claims."
                )
                out = llm.chat([
                    {"role":"system","content":"You write clear customer support documentation."},
                    {"role":"user","content":prompt},
                ])
                # If model returned one blob, keep it as playbook; still write fallback files too.
                write_text(out_dir / "PLAYBOOK.md", out)
        except Exception:
            pass

        write_text(out_dir / "SUPPORT_MACROS.md", pack["macros"])
        write_text(out_dir / "REFUND_POLICY.md", pack["refund"])
        write_text(out_dir / "TROUBLESHOOTING_FLOW.md", pack["troubleshooting"])
        write_text(out_dir / "KNOWN_ISSUES.md", pack["known_issues"])

        meta = {"generated_at": datetime.datetime.utcnow().isoformat()+"Z", "inbox_rows_used": len(inbox_rows)}
        write_text(out_dir / "meta.json", json.dumps(meta, indent=2))

        return ModuleResult(
            artifact_paths=[str(out_dir / "SUPPORT_MACROS.md"), str(out_dir / "REFUND_POLICY.md"), str(out_dir / "TROUBLESHOOTING_FLOW.md"), str(out_dir / "KNOWN_ISSUES.md"), str(out_dir / "meta.json")] + ([str(out_dir / "PLAYBOOK.md")] if (out_dir / "PLAYBOOK.md").exists() else []),
            metadata=meta
        )
