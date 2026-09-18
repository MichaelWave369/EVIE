from __future__ import annotations
from typing import Dict, Any
import json, datetime
from app.modules.base import ModuleResult, BaseModule
from app.export.packager import write_text
from app.rag.llm import LLM

def _fallback(topic: str) -> str:
    return f"""# Ecosystem Template Pack — {topic}

Alignment: 369 • Φ • Fib

## Notion Template (Markdown Export)
- Dashboard
- Inbox
- Projects (3 columns: Plan/Build/Ship)
- Weekly cadence (1/2/3/5/8)

## Canva Template (Design Brief)
- Square: 2000×2000 listing image
- Thumbnail: 1280×720
- KDP cover: 1600×2560
- Use Φ layout: 61.8% hero / 38.2% detail

## Figma Template (Spec)
- Frames: Cover, Thumbnail, Square
- Components: Header, Metric box, CTA strip, Footer microtext
"""

class EcosystemTemplatePacksModule(BaseModule):
    name = "ecosystem_template_packs"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        from app.flywheel.slug import slugify
        slug = slugify(topic)
        root = self.artifact_root(slug, "ecosystem_template_packs")

        llm = LLM()
        notion = llm.try_generate(
            f"""Create a Notion-ready template (as markdown) for '{topic}'.
Must include:
- 3 pillar dashboard (Create/Distribute/Compound)
- 6 loop tracker
- Fib publishing cadence (1/2/3/5/8)
- A 'Vault Intake' database schema section (properties list)
Keep it practical."""
        ) or _fallback(topic)

        canva = llm.try_generate(
            f"""Create a Canva design brief for '{topic}' template pack.
Include sizes (square 2000, thumb 1280x720, cover 1600x2560), layout guidelines using Phi ratio, and a checklist of elements.
Return markdown."""
) or """# Canva Design Brief\n\n- Square 2000×2000\n- Thumbnail 1280×720\n- Cover 1600×2560\n- Phi split: 61.8% hero, 38.2% details\n"""

        figma_spec = llm.try_generate(
            f"""Create a Figma template spec for '{topic}'.
Return JSON with frames, components, text styles, spacing (use 3/6/9 multiples) and export naming conventions."""
        )
        if not figma_spec:
            figma = {
                "topic": topic,
                "alignment": "369_phi_fib",
                "frames": [
                    {"name":"Cover","size":[1600,2560]},
                    {"name":"Thumbnail","size":[1280,720]},
                    {"name":"SquareListing","size":[2000,2000]},
                ],
                "spacing": [3,6,9,12,18,24,36],
                "components": ["Header","MetricBox","CTAStrip","FooterMicrotext","Badge369"],
                "export_naming": "topic_slug__frame__v###.png",
                "generated_at": datetime.datetime.utcnow().isoformat(),
            }
            figma_spec = json.dumps(figma, indent=2)

        manifest = {
            "topic": topic,
            "formats": ["notion_markdown","canva_brief","figma_spec_json"],
            "alignment": "369_phi_fib",
            "generated_at": datetime.datetime.utcnow().isoformat(),
        }

        notion_path = root / "notion_template.md"
        canva_path = root / "canva_design_brief.md"
        figma_path = root / "figma_template_spec.json"
        manifest_path = root / "manifest.json"
        checklist_path = root / "export_checklists.md"

        write_text(notion_path, notion)
        write_text(canva_path, canva)
        write_text(figma_path, figma_spec)
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        write_text(checklist_path, """# Export Checklists\n\n## Notion\n- Duplicate pages\n- Replace placeholder copy\n- Export as Markdown/PDF if desired\n\n## Canva\n- Duplicate designs\n- Swap hero image\n- Export PNG (sRGB)\n\n## Figma\n- Update styles\n- Export frames\n- Keep naming conventions\n""")

        return ModuleResult(
            artifact_paths=[str(notion_path), str(canva_path), str(figma_path), str(manifest_path), str(checklist_path)],
            metadata={"formats": manifest["formats"]},
        )
