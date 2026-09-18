from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import datetime, json

from app.modules.base import ModuleResult
from app.rag.llm import LLM
from app.settings import settings
from app.export.packager import write_text
from app.flywheel.slug import slugify

_PLATFORM_SPECS = {
    "kdp": {
        "label": "Amazon KDP (ebook + paperback)",
        "listing_fields": ["Title", "Subtitle", "Series", "Description", "Keywords (7)", "Categories", "Author", "Price", "A+ Content Plan"],
        "asset_checks": [
            "Cover: 1600x2560 (ebook), plus paperback wrap if needed",
            "Manuscript: clean markdown → export workflow",
            "Front matter: copyright, disclaimer, table of contents",
            "Back matter: CTA to next product + newsletter",
            "Keywords + categories: 3 primary, 6 secondary",
            "Blurb: 3 hooks + 6 bullets + 9 proof points",
        ],
        "qa_checks": [
            "No prohibited claims; soften absolutes",
            "Spelling/format consistent",
            "Series consistency (fonts, naming, promise)",
            "Preview readability",
            "Pricing ladder matches offer ladder",
            "Metadata matches topic + niche",
            "CTA links correct",
            "Disclaimer present if wellness/finance/etc",
            "Version/changelog noted",
        ],
    },
    "etsy": {
        "label": "Etsy (digital download)",
        "listing_fields": ["Title", "Description", "13 Tags", "Materials", "Occasion", "Who it's for", "What's included", "How to download", "Refund policy"],
        "asset_checks": [
            "Listing images: 5–10 mockups (square preferred)",
            "ZIP structure: /READ_ME_FIRST + /PRINTABLES or /TEMPLATES",
            "File formats: PDF + PNG + source (optional)",
            "Instructions: 3-step install/use",
            "Upsell note: bundle + next pack",
            "Support macros: top 9 responses",
        ],
        "qa_checks": [
            "Title front-loads keywords",
            "Tags unique (no duplicates)",
            "No IP violations / trademarks",
            "Files open cleanly",
            "Clear usage license",
            "Instant value communicated",
            "Refund expectations clear",
            "SEO: keywords appear in first 160 chars",
            "Version noted in README",
        ],
    },
    "gumroad": {
        "label": "Gumroad (digital product)",
        "listing_fields": ["Name", "Summary", "Full description", "Price", "Cover image", "FAQ", "License", "Order bump", "Upsell"],
        "asset_checks": [
            "content.zip with clear folder names",
            "Cover (square) + 3 promo images",
            "FAQ: 6 Qs, 9 support macros",
            "Order bump: 1 small add-on",
            "Upsell: premium tier",
            "Email sequence: 1/2/3/5/8 follow-ups",
        ],
        "qa_checks": [
            "Promise is specific + measurable",
            "Immediate first win in first page",
            "Files labeled clearly",
            "CTA points to next product",
            "No contradictory claims",
            "Pricing ladder makes sense",
            "Support load minimized",
            "Changelog included",
            "Refund terms included",
        ],
    },
    "youtube": {
        "label": "YouTube (videos + shorts)",
        "listing_fields": ["Title", "Description", "Chapters", "Tags", "Pinned comment", "Thumbnail concept", "Shorts cut list", "CTA"],
        "asset_checks": [
            "1 long script (8–12 min)",
            "3 shorts scripts (<=60s)",
            "Thumbnail directions: 3 variations",
            "Description: hook + value + links + disclaimer",
            "Chapters: 3–6 segments",
            "Pinned comment CTA",
        ],
        "qa_checks": [
            "Hook in first 10 seconds",
            "Single clear viewer promise",
            "No harmful/illegal advice",
            "Avoid medical/legal certainty language",
            "Chapters accurate",
            "CTA not spammy",
            "Repeatable series format",
            "Brand consistency",
            "Endscreen suggestion present",
        ],
    },
    "udemy": {
        "label": "Udemy (course)",
        "listing_fields": ["Course title", "Subtitle", "What you'll learn (3–6 bullets)", "Requirements", "Target students", "Curriculum outline", "Promo script"],
        "asset_checks": [
            "Curriculum: 3 sections × 3 lessons (starter)",
            "Worksheets + exercises",
            "Promo script + preview lecture plan",
            "FAQ + support macros",
            "Roadmap: next 5 updates (Fib)",
            "Certificate/bonus pack plan",
        ],
        "qa_checks": [
            "Learning outcomes clear",
            "No unrealistic guarantees",
            "Exercises included",
            "Audience fit strong",
            "Naming consistent",
            "Upsell path defined",
            "Support plan ready",
            "Changelog included",
            "Files organized",
        ],
    },
    "unity": {
        "label": "Unity Asset Store (pack)",
        "listing_fields": ["Title", "Category", "Description", "Version", "Docs", "Support email", "Keywords"],
        "asset_checks": [
            "Package manifest + folder structure",
            "Docs: install + quickstart",
            "Changelog: v001+",
            "Demo scene plan",
            "Screenshots list",
            "License/usage notes",
        ],
        "qa_checks": [
            "Files compile/run",
            "No third-party IP issues",
            "Docs sufficient",
            "Version consistent across files",
            "Support macros prepared",
            "Naming conventions consistent",
            "Readme included",
            "No secrets/tokens inside",
            "Test plan included",
        ],
    },
    "fab": {
        "label": "Fab (Unreal/3D assets)",
        "listing_fields": ["Title", "Description", "Supported engine versions", "Technical details", "License", "Keywords"],
        "asset_checks": [
            "Technical details sheet",
            "File structure + naming",
            "Screenshots/preview plan",
            "Docs + changelog",
            "Support macros",
            "Update roadmap (Fib)",
        ],
        "qa_checks": [
            "Performance considerations stated",
            "Compatibility stated",
            "No IP violations",
            "Docs included",
            "Versioned releases",
            "Keywords relevant",
            "Clear value proposition",
            "Support plan",
            "License clear",
        ],
    },
    "patreon": {
        "label": "Patreon (membership)",
        "listing_fields": ["Tier names", "Prices", "Benefits", "Welcome post", "Monthly calendar", "Content cadence"],
        "asset_checks": [
            "3 tiers: Entry/Core/Premium",
            "Monthly calendar: 1/2/3/5/8 cadence",
            "Welcome sequence (3 emails/posts)",
            "Benefit list: 3/6/9 format",
            "Retention hooks",
            "Community rules + FAQ",
        ],
        "qa_checks": [
            "Benefits sustainable",
            "Clear differentiation between tiers",
            "Cadence realistic",
            "Onboarding clear",
            "Support boundaries clear",
            "No prohibited claims",
            "Upsell path exists",
            "Brand consistency",
            "First month ready",
        ],
    },
    "substack": {
        "label": "Substack (newsletter)",
        "listing_fields": ["Publication name", "About", "Free vs paid benefits", "Pricing", "Welcome email", "Archive strategy"],
        "asset_checks": [
            "About page copy",
            "Free→Paid upgrade path",
            "Welcome series (3 messages)",
            "Weekly template",
            "Archive tags/categories plan",
            "Referral/CTA copy",
        ],
        "qa_checks": [
            "Clear promise",
            "Consistent cadence",
            "Paid benefits concrete",
            "Archive structured",
            "Calls-to-action tasteful",
            "Disclaimer where needed",
            "Brand consistency",
            "First 5 issues planned",
            "Upgrade copy ready",
        ],
    },
}

def _md_list(title: str, items: List[str]) -> str:
    return "### " + title + "\n" + "\n".join([f"- {x}" for x in items]) + "\n"

class PlatformPacksModule:
    name = "platform_packs"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        platforms = constraints.get("platforms") or ["gumroad","kdp","etsy","youtube"]
        platforms = [p.lower().strip() for p in platforms]
        platforms = [p for p in platforms if p in _PLATFORM_SPECS]
        if not platforms:
            platforms = ["gumroad"]

        artifact_paths = constraints.get("artifact_paths") or []
        include_artifacts = bool(constraints.get("include_artifacts", True))

        llm = LLM.from_settings()
        key = slugify(topic)
        out_root = Path(settings.data_dir) / "artifacts" / "platform_packs" / key
        out_root.mkdir(parents=True, exist_ok=True)

        created: List[str] = []
        meta = {"module": self.name, "topic": topic, "platforms": platforms, "include_artifacts": include_artifacts}

        for p in platforms:
            spec = _PLATFORM_SPECS[p]
            pdir = out_root / p
            pdir.mkdir(parents=True, exist_ok=True)

            # Core checklist
            checklist = f"""# Platform Pack — {spec['label']}

Topic: **{topic}**
Alignment: 369 • Φ • Fib

## Listing Fields (3×)
{_md_list("Fields", spec["listing_fields"])}

## Asset Checklist (6×)
{_md_list("Assets", spec["asset_checks"])}

## Quality Gates (9×)
{_md_list("QA", spec["qa_checks"])}

"""
            write_text(pdir / "CHECKLIST.md", checklist)
            created.append(str(pdir / "CHECKLIST.md"))

            # Listing copy (LLM assisted)
            prompt = f"""Write platform-optimized listing copy for:
Platform: {spec['label']}
Topic: {topic}

Constraints:
- Use 3 hooks, 6 bullets, 9 proof points.
- Keep claims realistic. Avoid guarantees.
- Include a short 'What's inside' section.
- Include a simple disclaimer line if the topic touches health/finance/legal.
Return in Markdown with headings: Hook, What You Get, Who It's For, How It Works, FAQ, Next Step CTA.
"""
            listing = llm.chat([{"role":"user","content":prompt}])
            write_text(pdir / "LISTING_COPY.md", listing)
            created.append(str(pdir / "LISTING_COPY.md"))

            # Import templates / structured fields
            fields = {
                "platform": p,
                "label": spec["label"],
                "topic": topic,
                "suggested_title_formula": "Keyword + Outcome + Timeframe (or 'Starter Kit')",
                "keywords_hint": ["primary_keyword", "secondary_keyword", "pain_point", "solution_phrase"],
                "tags_or_keywords": spec["listing_fields"],
            }
            write_text(pdir / "FIELDS.json", json.dumps(fields, indent=2))
            created.append(str(pdir / "FIELDS.json"))

            # If we have artifacts, generate mapping
            if include_artifacts and artifact_paths:
                map_md = "# Artifact Mapping\n\n"
                map_md += "These are the artifacts generated in this offer run (local paths).\n\n"
                for ap in artifact_paths:
                    map_md += f"- {ap}\n"
                map_md += "\nSuggested placement:\n"
                map_md += "- Put the main ZIP as the downloadable file.\n"
                map_md += "- Use cover/thumbnail images as listing media.\n"
                map_md += "- Use FAQ/support macros as listing FAQ.\n"
                write_text(pdir / "ARTIFACT_MAP.md", map_md)
                created.append(str(pdir / "ARTIFACT_MAP.md"))

        return ModuleResult(created, meta)
