from __future__ import annotations
from typing import Any
import time
from .base import ModuleResult
from .utils import ensure_dir, write_text, write_json, now_iso, FIB, slugify

CONTENT_TYPES = [
    "Issue (newsletter)", "Template/Checklist", "Mini lesson", "Office hours prompt", "Case study", "Challenge/assignment"
]

class MembershipDripCalendar:
    """3 tiers × 6 content types × 9 touchpoints per cycle."""
    name = "membership_drip_calendar"

    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        out_dir = f"{run_folder}/artifacts/{self.name}"
        ensure_dir(out_dir)

        tiers = constraints.get("tiers") or ["Bronze", "Silver", "Gold"]
        if isinstance(tiers, str):
            tiers = [tiers]
        cycle_days = int(constraints.get("cycle_days") or 21)
        touchpoints = int(constraints.get("touchpoints") or 9)

        # schedule on Fib days within cycle
        fib_days = [d for d in FIB if d <= cycle_days][:touchpoints]
        while len(fib_days) < touchpoints:
            fib_days.append(min(cycle_days, (fib_days[-1] + 1) if fib_days else 1))

        plan = []
        for ti,tname in enumerate(tiers):
            for j in range(touchpoints):
                plan.append({
                    "tier": tname,
                    "day": fib_days[j],
                    "content_type": CONTENT_TYPES[j % len(CONTENT_TYPES)],
                    "deliverable": f"{CONTENT_TYPES[j % len(CONTENT_TYPES)]} for {tname} — {topic}",
                })

        md = [f"# Membership Drip Calendar — {topic}", "", "## Structure", "- 3 tiers", "- 6 content types", "- 9 touchpoints per cycle", "", "## Cycle plan"]
        for p in plan:
            md.append(f"- Day {p['day']:>2} [{p['tier']}] — {p['content_type']}: {p['deliverable']}")
        md_path = f"{out_dir}/DRIP_CALENDAR.md"
        write_text(md_path, "\n".join(md))

        # simple .ics
        ics_lines = ["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//EmberVault//DripCalendar//EN"]
        start_ts = int(time.time())
        start_day0 = time.strftime("%Y%m%d", time.gmtime(start_ts))
        for idx,p in enumerate(plan[:touchpoints]):  # create one tier's touchpoints in calendar by default
            dt = time.strftime("%Y%m%d", time.gmtime(start_ts + (p["day"]-1)*86400))
            uid = f"{slugify(sku)}-{idx}@embervault"
            ics_lines += [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{start_day0}T000000Z",
                f"DTSTART;VALUE=DATE:{dt}",
                f"SUMMARY:{p['tier']} — {p['content_type']}",
                "END:VEVENT",
            ]
        ics_lines.append("END:VCALENDAR")
        ics_path = f"{out_dir}/drip_calendar.ics"
        write_text(ics_path, "\n".join(ics_lines))

        json_path = f"{out_dir}/drip_calendar.json"
        write_json(json_path, {"sku": sku, "topic": topic, "generated_at": now_iso(), "tiers": tiers, "cycle_days": cycle_days, "touchpoints": touchpoints, "plan": plan})
        return ModuleResult(name=self.name, artifacts=[md_path, ics_path, json_path], summary={"tiers": len(tiers), "touchpoints": touchpoints})
