"""
career_tools.py — EVIE Career & Job Search Module

Inspired by the top AI job tools: resume generation, cover letters,
interview prep, LinkedIn optimization, and career coaching content.
Monetize by selling these as digital products or coaching packages.
"""
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import datetime
from app.modules.base import ModuleResult
from app.rag.llm import LLM
from app.settings import settings
from app.export.packager import write_text


class CareerToolsModule:
    name = "career_tools"

    SUBTYPES = {
        "resume": "AI-powered resume tailored to a specific job/industry",
        "cover_letter": "Compelling cover letter matched to a job posting",
        "interview_prep": "Interview Q&A prep kit with sample answers",
        "linkedin_optimizer": "LinkedIn profile optimization guide",
        "career_pivot": "Career change roadmap and action plan",
        "salary_negotiation": "Salary negotiation scripts and talking points",
        "job_search_kit": "Complete job search bundle (resume + cover letter + interview + LinkedIn)",
        "personal_brand": "Personal brand statement and bio package",
        "networking_scripts": "Cold outreach + networking email templates",
        "layoff_bounce_back": "Post-layoff comeback plan + resources guide",
    }

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        llm = LLM.from_settings()
        subtype = constraints.get("subtype", "resume")
        target_role = constraints.get("target_role", topic)
        industry = constraints.get("industry", "Technology")
        experience_level = constraints.get("experience_level", "mid-level (3-7 years)")
        audience = constraints.get("audience", "job seekers")

        prompts = {
            "resume": f"""Create a professional, ATS-optimized resume template for:
Role: {target_role}
Industry: {industry}
Experience Level: {experience_level}

Include:
1. Professional Summary (3 sentences, keyword-rich)
2. Core Skills section (12-15 keywords in 3-column format)
3. Work Experience template (3 roles, STAR-format bullet points)
4. Education section
5. Optional: Certifications, Projects, Volunteer

Format: Clean markdown. Include [PLACEHOLDER] fields the buyer fills in.
Add a "Tips" section at the end with 5 ATS/recruiter optimization tips.
Make this a premium, sellable template worth $15-47.""",

            "cover_letter": f"""Create 3 professional cover letter templates for:
Role: {target_role}
Industry: {industry}

Template 1: "Story-driven" (starts with a compelling career moment)
Template 2: "Achievement-focused" (leads with 3 key wins)
Template 3: "Mission-aligned" (connects personal values to company)

Each template: ~300 words, with [PLACEHOLDER] fields.
Include a "Customization Guide" section.
Make these sellable as a $12-27 digital product.""",

            "interview_prep": f"""Create a comprehensive interview prep kit for:
Role: {target_role}
Industry: {industry}
Level: {experience_level}

Include:
1. Top 20 most common interview questions with model answers (STAR format)
2. 5 Technical/role-specific questions with answer frameworks
3. 10 behavioral questions with answer templates
4. "Questions to ask the interviewer" — 15 smart questions
5. Salary discussion scripts
6. Follow-up email templates (same-day + 48hr)
7. Pre-interview checklist (day-before + morning-of)

Make this a sellable $27-67 PDF kit.""",

            "linkedin_optimizer": f"""Create a LinkedIn Profile Optimization Guide for {target_role} in {industry}.

Include:
1. Headline formulas (5 variations ranked by click-through)
2. "About" section template (hook + story + CTA, 300 words)
3. Featured section strategy
4. Experience descriptions (achievement-first format)
5. Skills optimization (which 50 to pick for algorithm)
6. Content strategy for job seekers (what/when to post)
7. Connection request templates (cold + warm)
8. Profile photo tips checklist

Make this a sellable $19-37 guide.""",

            "career_pivot": f"""Create a Career Pivot Roadmap for someone moving into {target_role} from {industry}.

Include:
1. Transferable skills audit worksheet
2. Skill gap analysis + 90-day upskilling plan
3. Portfolio-building strategy (3 projects to create)
4. Networking strategy for new field (30-60-90 day plan)
5. Resume repositioning guide (how to reframe old experience)
6. Personal narrative script ("Why I'm making this change")
7. Target company research template
8. Income bridge strategies during transition

Make this a sellable $37-97 workbook.""",

            "salary_negotiation": f"""Create a Salary Negotiation Master Kit for {target_role} in {industry}.

Include:
1. Market research guide (how to find salary data)
2. Negotiation scripts for 5 scenarios:
   - Initial offer response
   - Counteroffer delivery
   - Handling "that's our max" pushback
   - Remote/relocation negotiation
   - Equity/bonus negotiation
3. Email templates for all scenarios
4. Non-salary negotiation items checklist (PTO, title, etc.)
5. Negotiation psychology tactics

Make this a sellable $27-47 kit.""",

            "job_search_kit": f"""Create a Complete Job Search Mega-Kit for {target_role} in {industry}.

This is a BUNDLE — create condensed but complete versions of:
1. Resume template (ATS-optimized)
2. Cover letter (2 templates)
3. Interview prep (top 15 Q&As)
4. LinkedIn optimization checklist
5. Job search tracker spreadsheet template (columns/structure)
6. Weekly job search schedule template
7. Networking email swipe file (5 templates)
8. Offer evaluation checklist

Include a "Quick Start Guide" page.
Make this a sellable $47-97 bundle.""",

            "personal_brand": f"""Create a Personal Brand Package for a {target_role} in {industry}.

Include:
1. Personal Brand Statement (3 versions: elevator pitch, LinkedIn, bio)
2. Professional bio templates (100-word + 300-word + long-form)
3. Brand messaging pillars (3-5 core themes)
4. Social media voice guide
5. Content pillars strategy (what to post about)
6. Speaking/media bio
7. Email signature template
8. "Expert positioning" content calendar (30 post ideas)

Make this a sellable $37-67 package.""",

            "networking_scripts": f"""Create a Networking & Cold Outreach Swipe File for {target_role} professionals.

Include 30+ templates for:
1. LinkedIn connection requests (5 types: cold, warm, mutual, event, post)
2. LinkedIn DM follow-ups (3 scenarios)
3. Cold email outreach (5 templates by goal)
4. Informational interview requests
5. Coffee chat follow-ups
6. Thank you notes (post-meeting, post-interview)
7. Referral requests
8. Reconnecting with old contacts
9. Conference/event follow-up templates
10. "I saw your work" genuine outreach templates

Make this a sellable $17-37 swipe file.""",

            "layoff_bounce_back": f"""Create a Post-Layoff Bounce-Back Action Plan for {industry} professionals.

Include:
1. First 48-hour action checklist (emotional + practical)
2. Benefits/unemployment checklist
3. 30-60-90 day job search roadmap
4. Resume refresh guide (position for new market)
5. References strategy
6. Leveraging severance time for skill-building
7. Mental health + momentum tips
8. Community + support resources
9. Financial bridge strategies
10. "Your layoff story" narrative script (interviews)

Make this a compassionate, practical, sellable $27-47 guide.""",
        }

        prompt = prompts.get(subtype, prompts["resume"])
        text = llm.chat([{"role": "user", "content": prompt}])

        out_dir = Path(settings.data_dir) / "artifacts" / "career_tools"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"career_{subtype}__{ts}.md"
        out_path = out_dir / filename
        write_text(out_path, text)

        return ModuleResult(
            artifact_paths=[str(out_path)],
            metadata={
                "topic": topic,
                "module": self.name,
                "subtype": subtype,
                "target_role": target_role,
                "industry": industry,
                "sell_price_range": _price_range(subtype),
            }
        )


def _price_range(subtype: str) -> str:
    ranges = {
        "resume": "$15–$47",
        "cover_letter": "$12–$27",
        "interview_prep": "$27–$67",
        "linkedin_optimizer": "$19–$37",
        "career_pivot": "$37–$97",
        "salary_negotiation": "$27–$47",
        "job_search_kit": "$47–$97",
        "personal_brand": "$37–$67",
        "networking_scripts": "$17–$37",
        "layoff_bounce_back": "$27–$47",
    }
    return ranges.get(subtype, "$19–$47")
