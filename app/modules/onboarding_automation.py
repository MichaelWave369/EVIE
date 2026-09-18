
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Dict as TDict
import datetime, csv, json

from app.modules.base import ModuleResult
from app.settings import settings
from app.flywheel.slug import slugify
from app.export.packager import write_text
from app.rag.llm import LLM

FIB_DAYS = [1,2,3,5,8]

def _load_leads(csv_path: Path) -> List[TDict[str, str]]:
    rows: List[TDict[str, str]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({k.strip(): (v or "").strip() for k,v in r.items()})
    return rows

def _segment(leads: List[TDict[str,str]]) -> TDict[str, List[TDict[str,str]]]:
    buckets: TDict[str, List[TDict[str,str]]] = {}
    for r in leads:
        seg = r.get("segment") or r.get("Segment") or r.get("tag") or r.get("Tag") or ""
        seg = seg.strip().lower() if seg else ""
        if not seg:
            src = (r.get("source") or r.get("Source") or "").lower()
            if "youtube" in src:
                seg = "video"
            elif "newsletter" in src or "substack" in src:
                seg = "newsletter"
            else:
                seg = "general"
        buckets.setdefault(seg, []).append(r)
    return buckets

def _fallback_sequence(topic: str, segment: str) -> str:
    return f"""# Onboarding Sequence — {topic} — Segment: {segment}

> IMPORTANT: Send only to **opted-in** subscribers. Include unsubscribe instructions.

## Fib cadence (1 / 2 / 3 / 5 / 8 days)

### Day 1 — Welcome (3 promises)
- Promise 1 (what they get)
- Promise 2 (how it works)
- Promise 3 (what to do next)

### Day 2 — Quick Win (6 steps)
- Step 1…Step 6

### Day 3 — Proof + Story (9 objections handled)
- Objection 1…Objection 9

### Day 5 — Offer Ladder
- Entry → Core → Premium (Φ ratio emphasis)

### Day 8 — Retention + Referral
- Invite them into community/membership + ask for a reply

## Compliance footer
- You are receiving this because you opted in.
- Unsubscribe: (your link or instruction)
"""

class OnboardingAutomationModule:
    name = "onboarding_automation"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        slug = slugify(topic)
        out_dir = settings.data_dir / "artifacts" / "onboarding_automation" / slug
        out_dir.mkdir(parents=True, exist_ok=True)

        leads_csv = constraints.get("leads_csv_path")
        leads: List[TDict[str,str]] = []
        if leads_csv:
            p = Path(leads_csv)
            if p.exists():
                leads = _load_leads(p)

        if not leads:
            # create a template
            template = "email,name,segment,source\nexample@example.com,Alex,general,leadmagnet\n"
            write_text(out_dir / "leads_import_template.csv", template)
            write_text(out_dir / "README.md",
                       "No leads CSV provided or file missing. Use leads_import_template.csv to prepare your list (opt-in only).")
            segments = {"general": []}
        else:
            segments = _segment(leads)

        sequences: Dict[str, str] = {}
        schedule_rows: List[Dict[str,str]] = []

        for seg, rows in segments.items():
            md = _fallback_sequence(topic, seg)
            # LLM refine per segment (optional)
            try:
                llm = LLM.from_settings()
                if llm.backend != "none" and bool(constraints.get("llm_refine", True)):
                    prompt = (
                        "Write an email onboarding sequence in Markdown. "
                        "Keep 5 emails at days 1,2,3,5,8. "
                        "Use 3/6/9 structure. Keep claims conservative. "
                        "Include unsubscribe/footer. "
                        f"Topic: {topic}. Segment: {seg}."
                    )
                    md = llm.chat([
                        {"role":"system","content":"You are an ethical email copywriter focused on opt-in newsletters."},
                        {"role":"user","content":prompt},
                    ])
            except Exception:
                pass

            sequences[seg] = md
            seq_path = out_dir / "sequences" / f"{seg}_sequence.md"
            write_text(seq_path, md)

            for day in FIB_DAYS:
                schedule_rows.append({
                    "segment": seg,
                    "day_offset": str(day),
                    "template_path": str(seq_path),
                    "note": "Send only to opted-in subscribers; include unsubscribe.",
                })

        # Write schedule
        sched_path = out_dir / "send_schedule.csv"
        sched_path.parent.mkdir(parents=True, exist_ok=True)
        with sched_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["segment","day_offset","template_path","note"])
            writer.writeheader()
            writer.writerows(schedule_rows)

        # Minimal CRM schema (local)
        write_text(out_dir / "local_crm_schema.sql", """-- Local CRM-lite schema (SQLite)
CREATE TABLE IF NOT EXISTS leads (
  lead_id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL UNIQUE,
  name TEXT,
  segment TEXT,
  source TEXT,
  status TEXT NOT NULL DEFAULT 'subscribed',
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS send_log (
  send_id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL,
  segment TEXT,
  day_offset INTEGER,
  sent_at TEXT,
  status TEXT,
  details_json TEXT
);
""")

        meta = {
            "generated_at": datetime.datetime.utcnow().isoformat()+"Z",
            "segments": list(segments.keys()),
            "lead_count": len(leads),
        }
        write_text(out_dir / "meta.json", json.dumps(meta, indent=2))

        artifacts = [str(out_dir / "send_schedule.csv"), str(out_dir / "local_crm_schema.sql"), str(out_dir / "meta.json")]
        if (out_dir / "leads_import_template.csv").exists():
            artifacts.append(str(out_dir / "leads_import_template.csv"))
        return ModuleResult(artifact_paths=artifacts, metadata=meta)
