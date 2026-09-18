from __future__ import annotations
from typing import Any
from .base import ModuleResult
from .utils import ensure_dir, write_text, write_json, now_iso, three_six_nine_sections

class WorkshopWebinarKit:
    """Workshop/webinar kit: run once, sell forever (recording + kit)."""
    name = "workshop_webinar_kit"

    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        out_dir = f"{run_folder}/artifacts/{self.name}"
        ensure_dir(out_dir)

        bullets3 = ["Teach (core idea)", "Demonstrate (live build)", "Activate (homework + follow-up)"]
        bullets6 = [
            "Slide deck outline (10–15 slides)",
            "Speaker notes (timed)",
            "Handout/workbook (printable)",
            "Follow-up email sequence (Fib)",
            "Replay landing page copy",
            "Offer pitch (entry/core/premium)"
        ]
        bullets9 = [
            "Open with a painful before-state",
            "Promise a bounded outcome (no guarantees)",
            "Show the exact framework",
            "Live demo: do 1 real artifact",
            "Invite questions (but keep scope)",
            "Give a 1-page handout",
            "End with next step + CTA",
            "Collect testimonials",
            "Bundle recording + kit as evergreen product"
        ]
        md = three_six_nine_sections(f"{topic} — Workshop/Webinar Kit", bullets3, bullets6, bullets9)

        slide_outline = """# Slide Deck Outline (369)

1. Title + outcome (1 min)
2. The problem (2 min)
3. The framework (3 min)
4. 3 pillars (3 min)
5. 6-step workflow (6 min)
6. 9 common mistakes (6 min)
7. Live demo setup (2 min)
8. Live demo build (10 min)
9. Q&A buffer (5 min)
10. Offer ladder + CTA (3 min)
"""

        speaker_notes = """# Speaker Notes (timed)

## 0–3 min
- Hook + what they’ll have at the end

## 3–9 min
- Teach the framework (3/6/9)

## 9–25 min
- Live demo (build one artifact)

## 25–30 min
- CTA: bundle + next steps + testimonial request
"""

        handout = """# Handout (printable)

## 3 pillars
- 
- 
- 

## 6 steps
1) 
2) 
3) 
4) 
5) 
6) 

## 9 checklist
1) 
2) 
3) 
4) 
5) 
6) 
7) 
8) 
9) 
"""

        emails = """# Follow-up Emails (Fib cadence)

- Day 1: Replay + handout link
- Day 2: Best questions recap
- Day 3: Case study (mini)
- Day 5: Offer ladder (soft)
- Day 8: Offer ladder (firm) + FAQ
"""

        replay_lp = f"""# Replay Landing Page (copy)

**Title:** {topic} — Replay + Kit  
**Outcome:** What you will have in 30 minutes (bounded, practical)  
**Includes:** Recording + slides + handout + templates + follow-up sequence  
**CTA:** Download the kit / Buy the bundle  
**FAQ:** Address objections safely (no guarantees).
"""

        paths = [
            f"{out_dir}/WORKSHOP_KIT.md",
            f"{out_dir}/SLIDE_DECK_OUTLINE.md",
            f"{out_dir}/SPEAKER_NOTES.md",
            f"{out_dir}/HANDOUT.md",
            f"{out_dir}/FOLLOWUP_EMAILS.md",
            f"{out_dir}/REPLAY_LANDING_PAGE.md",
            f"{out_dir}/workshop_kit.json",
        ]
        write_text(paths[0], md)
        write_text(paths[1], slide_outline)
        write_text(paths[2], speaker_notes)
        write_text(paths[3], handout)
        write_text(paths[4], emails)
        write_text(paths[5], replay_lp)
        write_json(paths[6], {"sku": sku, "topic": topic, "generated_at": now_iso(), "length_minutes": 30})

        return ModuleResult(name=self.name, artifacts=paths, summary={"slides": 10, "emails": 5})
