from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import datetime, json
from app.modules.base import ModuleResult
from app.rag.llm import LLM
from app.settings import settings
from app.export.packager import write_text


class MarketplaceAssetsModule:
    """Generate evergreen asset-pack bundles for marketplaces (Unity/Fab/general). Local-first: creates a folder
    with manifests, docs, changelog, and listing copy. You add the actual code/art later."""
    name = "marketplace_assets"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        llm = LLM.from_settings()
        target = constraints.get("target", "unity/fab")
        asset_type = constraints.get("asset_type", "toolkit (scripts + UI + docs)")
        license_hint = constraints.get("license", "personal + commercial tiers")
        version = constraints.get("version", "0.1.0")

        prompt = f"""Create a marketplace asset pack blueprint.

Topic: {topic}
Target marketplace: {target}
Asset type: {asset_type}
Version: {version}
License tiers: {license_hint}

Requirements:
- Local-first creator workflow.
- 369 / Φ / Fibonacci structure:
  - 3 pack pillars (Core / Extras / Docs)
  - 6 included items minimum, 9 recommended
  - Fibonacci roadmap (1,2,3,5,8) for updates
- Output sections:
  1) Pack name + tagline
  2) Folder structure
  3) Manifest JSON (assets, dependencies, versions)
  4) README + Quickstart
  5) CHANGELOG template
  6) Support FAQ
  7) Store listing copy (short + long) + SEO keywords + tags
"""

        text = llm.chat([{"role":"user","content":prompt}])
        out_dir = Path(settings.data_dir) / "artifacts" / "marketplace_assets"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        pack_dir = out_dir / f"asset_pack__{ts}"
        pack_dir.mkdir(parents=True, exist_ok=True)

        # Blueprint doc
        md_path = pack_dir / "PACK_BLUEPRINT.md"
        write_text(md_path, text)

        # Minimal manifest scaffold
        manifest = {
            "name": constraints.get("pack_name", f"{topic} Asset Pack"),
            "version": version,
            "target": target,
            "generated_at_utc": datetime.datetime.utcnow().isoformat() + "Z",
            "structure": {
                "core": ["Core/"],
                "extras": ["Extras/"],
                "docs": ["Docs/README.md", "Docs/CHANGELOG.md", "Docs/FAQ.md", "Docs/LICENSE.md"]
            },
            "notes": "Add your actual code/assets into Core/ and Extras/; update docs before publishing."
        }
        write_text(pack_dir / "manifest.json", json.dumps(manifest, indent=2))

        # Docs placeholders
        write_text(pack_dir / "Docs" / "README.md", "# README\n\n(Generated blueprint is in PACK_BLUEPRINT.md)\n")
        write_text(pack_dir / "Docs" / "CHANGELOG.md", f"# Changelog\n\n## {version} - {datetime.date.today().isoformat()}\n- Initial blueprint\n")
        write_text(pack_dir / "Docs" / "FAQ.md", "# FAQ\n\nQ: What is this?\nA: A local-first asset pack blueprint.\n")
        write_text(pack_dir / "Docs" / "LICENSE.md", "# License\n\n(Insert your license text and tier rules here.)\n")

        # Folder stubs
        (pack_dir / "Core").mkdir(exist_ok=True)
        (pack_dir / "Extras").mkdir(exist_ok=True)

        return ModuleResult(
            artifact_paths=[str(md_path), str(pack_dir / "manifest.json")],
            metadata={"topic": topic, "module": self.name, "pack_dir": str(pack_dir)}
        )
