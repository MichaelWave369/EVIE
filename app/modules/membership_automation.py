from __future__ import annotations
from typing import Dict, Any
import json, datetime
from app.modules.base import ModuleResult
from app.modules.base import BaseModule
from app.export.packager import write_text
from app.rag.llm import LLM

FIB = [1,2,3,5,8,13,21,34]

def _fallback(topic: str, constraints: Dict[str, Any]) -> str:
    niche = constraints.get("niche", "general")
    price_entry = constraints.get("price_entry", 9)
    price_core = constraints.get("price_core", 29)
    price_premium = constraints.get("price_premium", 99)
    return f"""# Membership + Paid Newsletter Automation — {topic}

**Niche:** {niche}  
**Alignment:** 369 • Φ • Fib  
**Goal:** recurring revenue via tiers + drip content + retention loops (local-only generator).

## 3 Tiers (Φ ladder)
1. **Entry — ${price_entry}/mo**: monthly drop + vault access (read-only)
2. **Core — ${price_core}/mo**: weekly drop + templates + community prompts
3. **Premium — ${price_premium}/mo**: monthly workshop pack + licensing bundle + priority Q&A

## 6 Content Pillars
- Foundations (why/what)
- How-To (steps)
- Templates (downloadables)
- Case Studies (proof)
- Challenges (community)
- Upgrades (new releases)

## 9 Recurring Automations
1. Topic mining from Vault → Top 9 ideas
2. 3-item weekly editorial board
3. Issue draft + CTA + upsell
4. Release calendar (Fib cadence)
5. Repurpose pack (blog + shorts + threads)
6. Onboarding email drip (1/2/3/5/8 days)
7. Retention nudges (30/60/90)
8. Support macros → FAQ updates
9. KPI recap capsule weekly

## Fib Drip (example)
Day 1: Welcome + quick win  
Day 2: “How it works” + ask 1 question  
Day 3: Deliver 1 template  
Day 5: Case study + invite upgrade  
Day 8: Bundle offer + limited-time bonus  

## Deliverables this module writes
- membership_plan.md
- welcome_emails.md
- drip_calendar.csv
- perks_matrix.json
"""

class MembershipAutomationModule(BaseModule):
    name = "membership_automation"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        from app.flywheel.slug import slugify
        slug = slugify(topic)
        root = self.artifact_root(slug, "membership_automation")

        llm = LLM()
        prompt = f"""Create a membership + paid newsletter automation blueprint for: {topic}.
Rules:
- Local-only operations (no cloud storage assumed)
- Enforce 369 / Phi / Fibonacci alignment
- Output sections: tiers, pillars, onboarding drip (Fib days), 30/60/90 retention, and a 4-week content calendar.
- Avoid medical/legal/guaranteed income claims. Use neutral language.
Return as Markdown."""

        md = llm.try_generate(prompt) or _fallback(topic, constraints)

        # Write plan
        plan_path = root / "membership_plan.md"
        write_text(plan_path, md)

        # Welcome + drip emails (template set)
        emails = llm.try_generate(
            f"""Write 5 short onboarding emails for the membership '{topic}' on days 1,2,3,5,8.
Each email: Subject + Body + CTA. Tone: {constraints.get('tone','warm, practical')}.
Include one soft upsell in emails 5 and 8. No exaggerated promises."""
        ) or """# Onboarding Emails (Days 1/2/3/5/8)\n\n(LLM disabled — add your copy here.)\n"""
        emails_path = root / "welcome_emails.md"
        write_text(emails_path, emails)

        # Drip calendar CSV
        rows = [
            [1, "Welcome + Quick Win", "Deliver immediate value + set expectation"],
            [2, "How it works", "Explain cadence + where to find downloads"],
            [3, "Template Drop", "Deliver a template + show usage"],
            [5, "Case Study", "Show proof + invite upgrade"],
            [8, "Bundle Offer", "Offer an upsell bundle + bonus"],
            [13, "Retention Check-in", "Ask 1 question + collect feedback"],
            [21, "Upgrade Spotlight", "Highlight premium perk + remind of library"],
            [34, "Seasonal Refresh", "Update roadmap + upcoming releases"],
        ]
        csv_lines = ["day,title,goal"] + [",".join(map(lambda x: str(x).replace(',',';'), r)) for r in rows]
        drip_path = root / "drip_calendar.csv"
        write_text(drip_path, "\n".join(csv_lines) + "\n")

        # Perks matrix JSON
        perks = {
            "topic": topic,
            "alignment": "369_phi_fib",
            "tiers": [
                {"name":"Entry","price_monthly": constraints.get("price_entry", 9), "perks":["Monthly drop","Vault access (read-only)","1 template/month"]},
                {"name":"Core","price_monthly": constraints.get("price_core", 29), "perks":["Weekly drop","Template packs","Community challenge prompts","Quarterly bundle discount"]},
                {"name":"Premium","price_monthly": constraints.get("price_premium", 99), "perks":["Monthly workshop pack","Licensing bundle","Priority Q&A","Early access releases"]},
            ],
            "generated_at": datetime.datetime.utcnow().isoformat(),
        }
        perks_path = root / "perks_matrix.json"
        perks_path.write_text(json.dumps(perks, indent=2), encoding="utf-8")

        return ModuleResult(
            artifact_paths=[str(plan_path), str(emails_path), str(drip_path), str(perks_path)],
            metadata={"tiers": [t["name"] for t in perks["tiers"]], "fib_days": FIB},
        )
