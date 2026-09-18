from __future__ import annotations
from typing import Any
from .base import ModuleResult
from .utils import ensure_dir, write_text, write_json, now_iso, three_six_nine_sections

class PromptLibraryGenerator:
    """Generate curated prompt packs for niches (fast, high-ROI digital product)."""
    name = "prompt_library_generator"

    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        niches = constraints.get("niches") or ["wellness practitioner", "creator", "small business"]
        if isinstance(niches, str):
            niches = [niches]
        pack_size = int(constraints.get("pack_size") or 27)  # 3x9 default
        out_dir = f"{run_folder}/artifacts/{self.name}"
        ensure_dir(out_dir)

        bullets3 = ["Discovery prompts", "Creation prompts", "Optimization prompts"]
        bullets6 = [
            "System prompt templates (safe + scoped)",
            "User prompt templates (copy/paste)",
            "Follow-up chains (Fib: 1/2/3/5/8)",
            "Quality gate checklist (no hype)",
            "Niche variants (3–9)",
            "Packaging for Gumroad/Etsy"
        ]
        bullets9 = [
            "Always include constraints + success criteria",
            "Ask for missing inputs explicitly",
            "Avoid medical/legal guarantees",
            "Use 369 structure in outputs",
            "Use Φ split for long docs (61.8/38.2)",
            "Use Fib cadence for follow-ups",
            "Include examples + counterexamples",
            "Include a 'short' and 'deep' version",
            "Include a 'data you need' section"
        ]
        md = three_six_nine_sections(f"{topic} — Prompt Library Pack (369)", bullets3, bullets6, bullets9)

        packs = []
        md += "\n\n---\n\n## Prompt Packs\n"
        for niche in niches:
            md += f"\n### Niche: {niche}\n"
            system = f"""You are a local-first assistant helping a user in the niche: {niche}.
Rules:
- Be practical and specific.
- Use 3/6/9 structure when helpful.
- Do not make guarantees.
- Ask clarifying questions only when needed; otherwise make reasonable assumptions and label them."""
            prompts = []
            # 9 prompts per niche (cap by pack_size overall across niches)
            base_prompts = [
                ("Discovery — map the situation", "Help me understand my goal, constraints, audience, and success metrics."),
                ("Discovery — diagnose blockers", "Identify the top 3 blockers and give a 6-step fix plan."),
                ("Discovery — define offer", "Turn this into an offer ladder (entry/core/premium) with a Phi price ladder."),
                ("Create — generate outline", "Generate a structured outline using 3 pillars, 6 sections, 9 bullets each."),
                ("Create — write draft", "Draft the first version. Keep it short, clean, and action-oriented."),
                ("Create — make templates", "Create reusable templates/checklists that I can sell as a pack."),
                ("Optimize — test plan", "Create an A/B test plan (3 variants) and a Fib schedule for iteration."),
                ("Optimize — objections", "List objections and write an FAQ that answers them safely."),
                ("Optimize — repurpose", "Repurpose this into: newsletter, YouTube, 3 social posts, lead magnet snippet.")
            ]
            for title, user in base_prompts:
                prompts.append({
                    "title": title,
                    "system": system,
                    "user": user,
                    "followups": [
                        "Make it shorter (1-page).",
                        "Make it deeper (add examples).",
                        "Add a checklist.",
                        "Add a FAQ.",
                        "Add a launch plan (Fib cadence)."
                    ]
                })
            packs.append({"niche": niche, "system": system, "prompts": prompts})

            # render to markdown
            md += "\n**System Prompt**\n\n```\n" + system + "\n```\n"
            for i,p in enumerate(prompts, start=1):
                md += f"\n**{i}. {p['title']}**\n\n_User prompt_\n\n```\n{p['user']}\n```\n"
                md += "_Follow-ups (Fib)_\n" + "\n".join([f"- {x}" for x in p["followups"]]) + "\n"

        write_text(f"{out_dir}/PROMPT_PACK.md", md)
        write_json(f"{out_dir}/prompt_pack.json", {"sku": sku, "topic": topic, "generated_at": now_iso(), "packs": packs, "pack_size_hint": pack_size})
        return ModuleResult(name=self.name, artifacts=[f"{out_dir}/PROMPT_PACK.md", f"{out_dir}/prompt_pack.json"], summary={"niches": niches, "count": len(niches)*9})
