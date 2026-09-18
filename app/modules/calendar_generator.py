from __future__ import annotations

from pathlib import Path
from typing import Dict, Any
import datetime

from app.modules.base import ModuleResult, BaseModule
from app.export.packager import write_text
from app.flywheel.slug import slugify


def _fmt_dt(dt: datetime.datetime) -> str:
    # iCal UTC time
    return dt.strftime("%Y%m%dT%H%M%SZ")


def build_ics(topic: str, start_dt: datetime.datetime, tz_note: str = "UTC") -> str:
    # Fib cadence + 3/6/9 structure:
    # 3 pillars across a 21-day sprint (1,2,3,5,8,13,21)
    fib = [0, 1, 2, 3, 5, 8, 13, 21]
    beats = [
        ("CREATE", "Create assets batch"),
        ("DISTRIBUTE", "Prep distribution + repurpose"),
        ("COMPOUND", "Optimize listing + support + iterate"),
    ]

    uid_base = f"EV369-{slugify(topic)}"
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//EmberVault//IncomeEngine//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{topic} — 369/Φ/Fib Release Calendar",
        f"X-WR-TIMEZONE:{tz_note}",
    ]

    now = datetime.datetime.utcnow()

    for day in fib[1:]:
        for i, (pillar, label) in enumerate(beats):
            dt = start_dt + datetime.timedelta(days=day, hours=i * 2)
            dt_end = dt + datetime.timedelta(minutes=45)
            uid = f"{uid_base}-{day}-{pillar}@local"
            summary = f"{pillar}: {topic} — Day {day}"

            desc = (
                f"{label}\n\n"
                f"369 Loop: Create → Distribute → Compound\n"
                f"Φ split: 61.8% create / 38.2% optimize\n"
                f"Fib cadence checkpoint: {day} day(s)\n"
            )
            desc_escaped = desc.replace("\n", "\\n")

            lines += [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{_fmt_dt(now)}",
                f"DTSTART:{_fmt_dt(dt)}",
                f"DTEND:{_fmt_dt(dt_end)}",
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{desc_escaped}",
                "END:VEVENT",
            ]

    lines.append("END:VCALENDAR")
    return "\n".join(lines) + "\n"


class CalendarGeneratorModule(BaseModule):
    name = "calendar_generator"
    display_name = "Calendar Generator (.ics)"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        start_date = constraints.get("start_date")
        if start_date:
            try:
                d = datetime.date.fromisoformat(start_date)
            except Exception:
                d = datetime.date.today()
        else:
            d = datetime.date.today()

        # Start at 09:00 UTC by default
        start_dt = datetime.datetime(d.year, d.month, d.day, 9, 0, 0)
        ics = build_ics(topic, start_dt)

        out = Path("data/artifacts/calendar") / slugify(topic)
        path = out / "release_calendar.ics"
        write_text(path, ics)

        return ModuleResult(
            artifact_paths=[str(path)],
            metadata={"start_date": str(d), "days": [1, 2, 3, 5, 8, 13, 21], "format": "ics"},
        )
