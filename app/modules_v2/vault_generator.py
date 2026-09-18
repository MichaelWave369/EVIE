from __future__ import annotations
from typing import Any
import os
from .base import ModuleResult
from .utils import ensure_dir, write_text, write_json, slugify, now_iso

class VaultGenerator:
    """Generate a Notion/Obsidian-style 'second brain' starter vault, structured by 369 + domains."""
    name = "vault_generator"

    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        apps = constraints.get("apps") or ["obsidian", "notion"]
        if isinstance(apps, str):
            apps = [apps]
        out_dir = f"{run_folder}/artifacts/{self.name}/{slugify(topic)}"
        ensure_dir(out_dir)

        # 12-domain scaffold (fits your Cell/Domain idea without requiring the full 20736 file)
        domains = [{"id": i, "name": f"Domain {i:02d}"} for i in range(1, 13)]
        phases = [{"id": i, "name": f"Phase {i:02d}"} for i in range(1, 13)]

        artifacts = []
        if "obsidian" in [a.lower() for a in apps]:
            vault = os.path.join(out_dir, "ObsidianVault")
            ensure_dir(vault)
            ensure_dir(os.path.join(vault, "00_Home"))
            ensure_dir(os.path.join(vault, "01_Domains"))
            ensure_dir(os.path.join(vault, "02_Phases"))
            ensure_dir(os.path.join(vault, "03_Templates"))
            ensure_dir(os.path.join(vault, "04_Logs"))

            write_text(os.path.join(vault, "00_Home", "START_HERE.md"), f"""# {topic} — Second Brain Vault

This vault is structured for **369 flow**:

- **3** Pillars: Capture → Organize → Ship  
- **6** Workflows: Research, Draft, Package, Publish, Support, Iterate  
- **9** Artifacts per product cycle (ideas → drafts → listings → proof)

## How to use
1) Capture notes into **04_Logs**
2) File into a Domain + Phase
3) Promote into a Product pack (your flywheel)
""")
            for d in domains:
                write_text(os.path.join(vault, "01_Domains", f"D{d['id']:02d}.md"), f"""# D{d['id']:02d} — {d['name']}

## What belongs here
- Notes, references, drafts, templates

## 369 tags
- #pillar/capture
- #pillar/organize
- #pillar/ship
""")
            for p in phases:
                write_text(os.path.join(vault, "02_Phases", f"P{p['id']:02d}.md"), f"""# P{p['id']:02d} — {p['name']}

## Checklist (6)
1) Define goal
2) Gather sources
3) Draft
4) Package
5) Publish
6) Iterate
""")
            write_text(os.path.join(vault, "03_Templates", "NOTE_TEMPLATE.md"), """# Note Title

**Context:**  
**Decision:**  
**Next step (Fib):** 1/2/3/5/8 days

## 3 key points
- 
- 
- 

## References
- 
""")
            artifacts += [
                os.path.join(vault, "00_Home", "START_HERE.md"),
                os.path.join(vault, "03_Templates", "NOTE_TEMPLATE.md"),
            ]

        if "notion" in [a.lower() for a in apps]:
            notion_dir = os.path.join(out_dir, "NotionExport")
            ensure_dir(notion_dir)
            # Notion import-friendly markdown + a database schema CSV
            write_text(os.path.join(notion_dir, "README_NOTION_IMPORT.md"), """# Notion Import (Local Files)

Notion can import Markdown pages. This folder includes:
- `HOME.md` (homepage)
- `DATABASE_SCHEMA.csv` (suggested DB properties)
- `PAGES/` (domain + phase pages)

Tip: create a database using the schema, then import pages and link them.
""")
            ensure_dir(os.path.join(notion_dir, "PAGES"))
            write_text(os.path.join(notion_dir, "HOME.md"), f"""# {topic} — Notion Second Brain

## 3 pillars
- Capture
- Organize
- Ship

## 6 workflows
- Research
- Draft
- Package
- Publish
- Support
- Iterate

## 9 artifacts per cycle
- Idea → Brief → Draft → Template → Listing → Media → QA → Launch → Review
""")
            # schema csv
            schema_csv = "Property,Type,Notes\nTitle,Title,Page title\nDomain,Select,D01..D12\nPhase,Select,P01..P12\nStatus,Select,idea/draft/shipping/live\nSKU,Text,Optional\nTags,Multi-select,Optional\nCreated,Date,\n"
            write_text(os.path.join(notion_dir, "DATABASE_SCHEMA.csv"), schema_csv)
            for d in domains:
                write_text(os.path.join(notion_dir, "PAGES", f"D{d['id']:02d}.md"), f"""# D{d['id']:02d} — {d['name']}

Use this page as a hub. Add links to notes, products, and workflows.
""")
            for p in phases:
                write_text(os.path.join(notion_dir, "PAGES", f"P{p['id']:02d}.md"), f"""# P{p['id']:02d} — {p['name']}

## Prompts
- What is the outcome?
- What is the smallest shippable artifact?
- What is the next Fib step?
""")
            artifacts += [
                os.path.join(notion_dir, "HOME.md"),
                os.path.join(notion_dir, "DATABASE_SCHEMA.csv"),
                os.path.join(notion_dir, "README_NOTION_IMPORT.md"),
            ]

        write_json(os.path.join(out_dir, "vault_manifest.json"), {"sku": sku, "topic": topic, "generated_at": now_iso(), "apps": apps, "domains": domains, "phases": phases})
        artifacts.append(os.path.join(out_dir, "vault_manifest.json"))

        return ModuleResult(name=self.name, artifacts=artifacts, summary={"apps": apps, "domains": 12, "phases": 12})
