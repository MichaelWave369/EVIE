from __future__ import annotations
from typing import Dict, Any, List
import json, datetime, re
from pathlib import Path
from app.modules.base import ModuleResult, BaseModule
from app.export.packager import write_text
from app.rag.llm import LLM

def _extract_listing_copy(artifact_paths: List[str]) -> str:
    for p in artifact_paths or []:
        if p.endswith("LISTING_COPY.md") or p.endswith("listing_copy.md"):
            try:
                return Path(p).read_text(encoding="utf-8")[:4000]
            except Exception:
                pass
    return ""

class MarketplaceListingOptimizerModule(BaseModule):
    name = "marketplace_listing_optimizer"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        from app.flywheel.slug import slugify
        slug = slugify(topic)
        root = self.artifact_root(slug, "marketplace_listing_optimizer")

        platforms = constraints.get("platforms") or ["gumroad","etsy","kdp","youtube"]
        artifact_paths = constraints.get("artifact_paths", [])
        base_copy = constraints.get("base_copy") or _extract_listing_copy(artifact_paths)

        llm = LLM()
        prompt = f"""Optimize marketplace listing copy for: {topic}
Platforms: {platforms}
Input copy (may be empty):
{base_copy}

Rules:
- Provide 3 title variants per platform (short/medium/long)
- Provide keyword/tag suggestions (platform-appropriate)
- Provide 6 bullets (benefits) + 3 disclaimers (no exaggerated promises)
- Provide a 3/6/9 A/B test plan and Fibonacci cadence.
Return as JSON with keys per platform."""
        out = llm.try_generate(prompt)

        if not out:
            # Fallback deterministic output
            payload = {}
            for pl in platforms:
                payload[pl] = {
                    "titles": [
                        f"{topic} — Starter Pack",
                        f"{topic} — 369/Φ/Fib Toolkit",
                        f"{topic} — Complete Offer Bundle (Local-Only)",
                    ],
                    "keywords": [topic.lower(), "template", "checklist", "guide", "bundle", "local-first", "automation"],
                    "bullets": [
                        "Clear 3-step structure to start",
                        "6 supporting checklists and trackers",
                        "9 automation hooks to reuse",
                        "Local-only files and export packs",
                        "Versioned releases + changelog",
                        "Includes support macros + FAQs",
                    ],
                    "disclaimers": [
                        "Educational content; review before publishing.",
                        "No guarantees of income or results.",
                        "Platform rules vary; validate before upload.",
                    ],
                }
            payload["ab_plan"] = {"headlines": 3, "thumbnails": 3, "descriptions": 3, "cadence_days":[1,2,3,5,8,13] }
            out = json.dumps(payload, indent=2)

        # Write files
        json_path = root / "optimized_listings.json"
        md_path = root / "optimized_listings.md"
        json_path.write_text(out, encoding="utf-8")

        # Also produce a readable markdown summary
        try:
            data = json.loads(out)
            md_lines = [f"# Marketplace Listing Optimizer — {topic}", "", f"Generated: {datetime.datetime.utcnow().isoformat()}", ""]
            for pl in platforms:
                d = data.get(pl, {})
                md_lines += [f"## {pl.upper()}", ""]
                titles = d.get("titles", [])
                if titles:
                    md_lines.append("**Titles**")
                    for t in titles:
                        md_lines.append(f"- {t}")
                    md_lines.append("")
                kws = d.get("keywords", [])
                if kws:
                    md_lines.append("**Keywords/Tags**")
                    md_lines.append(", ".join(kws))
                    md_lines.append("")
                bullets = d.get("bullets", [])
                if bullets:
                    md_lines.append("**Bullets**")
                    for b in bullets:
                        md_lines.append(f"- {b}")
                    md_lines.append("")
                disc = d.get("disclaimers", [])
                if disc:
                    md_lines.append("**Disclaimers**")
                    for x in disc:
                        md_lines.append(f"- {x}")
                    md_lines.append("")
            write_text(md_path, "\n".join(md_lines))
        except Exception:
            write_text(md_path, f"# Marketplace Listing Optimizer — {topic}\n\n(See optimized_listings.json)\n")

        return ModuleResult(
            artifact_paths=[str(json_path), str(md_path)],
            metadata={"platforms": platforms},
        )
