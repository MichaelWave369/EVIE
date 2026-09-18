from __future__ import annotations
from typing import Dict, Any, List
import json, datetime, re
from pathlib import Path
from app.modules.base import ModuleResult, BaseModule
from app.export.packager import write_text
from app.rag.llm import LLM

def _find_existing_pages(artifact_paths: List[str]) -> List[str]:
    pages = []
    for p in artifact_paths or []:
        if p.endswith(".md") and ("programmatic_seo" in p or "seo_engine" in p):
            pages.append(p)
    return pages[:50]

class AffiliateSiteModeModule(BaseModule):
    name = "affiliate_site_mode"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        from app.flywheel.slug import slugify
        slug = slugify(topic)
        root = self.artifact_root(slug, "affiliate_site_mode")
        site = root / "site"
        (site / "pages").mkdir(parents=True, exist_ok=True)

        artifact_paths = constraints.get("artifact_paths", [])
        existing_pages = _find_existing_pages(artifact_paths)

        llm = LLM()
        disclosure = """# Disclosure\n\nSome links may be affiliate links. If you click and purchase, we may earn a commission at no extra cost to you.\nWe only recommend tools we believe are useful.\n"""
        index = llm.try_generate(
            f"""Write a homepage (Markdown) for an affiliate content site about '{topic}'.
Structure:
- Hook
- 3 pillars
- 6 top guides
- 9 recommended tools section (no brand names required)
Include an explicit disclosure paragraph."""
        ) or f"""# {topic}\n\n{disclosure}\n\n## 3 Pillars\n1. Create\n2. Distribute\n3. Compound\n\n## 6 Guides\n- Getting started\n- Tool stack\n- Templates\n- Mistakes\n- Scaling\n- FAQ\n"""

        best_page = llm.try_generate(
            f"""Create a 'Best Tools for {topic}' page in Markdown.
Include:
- a comparison table template
- short buyer guide
- FAQ\n
Do not make guaranteed claims."""
        ) or """# Best Tools\n\n## Comparison Table\n| Tool | Best for | Notes |\n|---|---|---|\n| (A) | | |\n\n## Buyer guide\n- Define your goal\n- Match constraints\n\n## FAQ\n- ...\n"""

        link_map = {
            "topic": topic,
            "generated_at": datetime.datetime.utcnow().isoformat(),
            "pages": [],
            "source_pages_detected": existing_pages,
        }

        # Write core files
        readme_path = site / "README.md"
        config_path = site / "site_config.json"
        index_path = site / "pages" / "index.md"
        disclosure_path = site / "pages" / "disclosure.md"
        best_path = site / "pages" / f"best_{slug}.md"

        write_text(readme_path, """# Affiliate Site Mode (Local Export)\n\nThis folder is a static-site starter.\n- Put pages/ into any static site generator or simple markdown host.\n- Update the disclosure and add your affiliate IDs manually.\n\nLocal-only: generated offline from your Vault.\n""")
        config_path.write_text(json.dumps({
            "site_name": f"{topic} — Resource Hub",
            "slug": slug,
            "alignment": "369_phi_fib",
            "created_at": datetime.datetime.utcnow().isoformat(),
        }, indent=2), encoding="utf-8")

        write_text(index_path, index)
        write_text(disclosure_path, disclosure)
        write_text(best_path, best_page)

        link_map["pages"] = [str(index_path), str(disclosure_path), str(best_path)]
        link_map_path = site / "link_map.json"
        link_map_path.write_text(json.dumps(link_map, indent=2), encoding="utf-8")

        return ModuleResult(
            artifact_paths=[str(readme_path), str(config_path), str(index_path), str(disclosure_path), str(best_path), str(link_map_path)],
            metadata={"source_pages_detected": len(existing_pages), "pages": 3},
        )
