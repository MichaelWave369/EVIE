from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Tuple
import datetime
import json

from PIL import Image, ImageDraw, ImageFont

from app.modules.base import ModuleResult
from app.settings import settings
from app.flywheel.slug import slugify
from app.export.packager import write_text
from app.modules.pod_pack_generator import _default_phrases, _make_png, _make_svg, _watermark_text


def _mk_listing(topic: str, family: str) -> str:
    # 3 / 6 / 9 structure for platform listing copy
    fam = family.replace("_", " ").title()
    return (
        f"# POD Listing — {fam}\n\n"
        f"**Theme:** {topic}\n\n"
        "## 3 title ideas\n"
        f"1) {topic} — {fam} Design\n"
        f"2) 369 • Φ • Fib — {fam} — {topic}\n"
        f"3) Minimal Systems {fam}: {topic}\n\n"
        "## 6 bullets\n"
        "- Clean, readable design (template-generated)\n"
        "- Includes 9 variations (3 families × 3)\n"
        "- Organized folders for quick upload\n"
        "- Watermark/stamp text included (remove for final print files if needed)\n"
        "- Mockup images included for listing previews\n"
        "- Local-first workflow (no cloud required)\n\n"
        "## 9 keywords\n"
        "- 369\n- phi\n- fibonacci\n- minimal\n- local-first\n- systems\n- creator\n- workflow\n- productivity\n\n"
        "## Notes\n"
        "- Review local laws/platform rules.\n"
        "- Verify print dimensions per provider.\n\n"
        "Alignment: 369 • Φ • Fib\n"
    )


def _make_mockup(bg: Tuple[int, int, int], title: str, design_png: Path, out_path: Path, silhouette: str) -> None:
    w, h = 2000, 2000
    img = Image.new("RGBA", (w, h), (*bg, 255))
    d = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    # silhouette area
    box = (int(w*0.18), int(h*0.18), int(w*0.82), int(h*0.82))
    if silhouette == "mug":
        # mug body
        d.rounded_rectangle(box, radius=80, fill=(255,255,255,220), outline=(0,0,0,40), width=4)
        # handle
        hx0, hy0, hx1, hy1 = int(w*0.78), int(h*0.38), int(w*0.92), int(h*0.62)
        d.ellipse((hx0, hy0, hx1, hy1), outline=(0,0,0,60), width=18)
        d.ellipse((hx0+40, hy0+40, hx1-40, hy1-40), outline=(0,0,0,0), fill=(*bg, 255))
    elif silhouette == "sticker":
        d.rounded_rectangle(box, radius=140, fill=(255,255,255,235), outline=(0,0,0,50), width=6)
    elif silhouette == "poster":
        d.rectangle(box, fill=(255,255,255,235), outline=(0,0,0,60), width=6)
    elif silhouette == "tote":
        d.rounded_rectangle(box, radius=40, fill=(255,255,255,235), outline=(0,0,0,50), width=6)
        # handles
        d.arc((int(w*0.28), int(h*0.08), int(w*0.46), int(h*0.28)), 0, 180, fill=(0,0,0,60), width=12)
        d.arc((int(w*0.54), int(h*0.08), int(w*0.72), int(h*0.28)), 0, 180, fill=(0,0,0,60), width=12)
    else:
        # default tee/hoodie silhouette as rounded rect
        d.rounded_rectangle(box, radius=60, fill=(255,255,255,235), outline=(0,0,0,50), width=6)

    # paste design
    if design_png.exists():
        design = Image.open(design_png).convert("RGBA")
        # crop transparent margins roughly by bounding box
        bbox = design.getbbox()
        if bbox:
            design = design.crop(bbox)
        target_w = int(w * 0.46)
        target_h = int(h * 0.46)
        design.thumbnail((target_w, target_h))
        px = (w - design.size[0]) // 2
        py = int(h * 0.36)
        img.alpha_composite(design, (px, py))

    # title header
    d.text((int(w*0.05), int(h*0.05)), title[:60], font=font, fill=(0,0,0,220))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)


class PODSuperPackModule:
    """POD listing + mockup superpack (local-first).

    Extends POD packs with:
      - multiple product families (tee/hoodie/mug/sticker/poster/tote)
      - per-family listing copy
      - mockup images (2 per family)
      - print manifest

    Uses deterministic Pillow templates for mockups (no external services).
    """

    name = "pod_superpack"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        key = slugify(topic)
        out_root = Path(settings.data_dir) / "artifacts" / "pod_superpack" / key
        designs_dir = out_root / "designs"
        packs_dir = out_root / "packs"
        designs_dir.mkdir(parents=True, exist_ok=True)
        packs_dir.mkdir(parents=True, exist_ok=True)

        # Base designs (reuse the standard 9 phrases)
        size = constraints.get("size") or [4500, 5400]
        w, h = int(size[0]), int(size[1])
        phrases = constraints.get("phrases")
        phrase_list = list(phrases) if isinstance(phrases, list) and phrases else _default_phrases(topic)
        phrase_list = (phrase_list + _default_phrases(topic))[:9]

        sku_hint = str(constraints.get("sku") or f"EV369-{key}")
        stamp = _watermark_text(sku_hint)

        artifacts: List[str] = []

        for i, text in enumerate(phrase_list, start=1):
            design_id = f"design_{i:02d}"
            svg_path = designs_dir / f"{design_id}.svg"
            png_path = designs_dir / f"{design_id}.png"
            write_text(svg_path, _make_svg(text=text, size=(w, h), stamp=stamp))
            _make_png(text=text, size=(w, h), stamp=stamp, out_path=png_path)
            artifacts.extend([str(svg_path), str(png_path)])

        # Families
        families = constraints.get("families") or ["tshirt", "hoodie", "mug", "sticker", "poster", "tote"]
        families = [str(f).strip().lower() for f in families if str(f).strip()]
        families = families[:9]  # 9 max for the 369 motif

        # Use first design as the preview design for mockups
        preview_design = designs_dir / "design_01.png"

        manifest = {
            "module": self.name,
            "topic": topic,
            "created_at": datetime.datetime.utcnow().isoformat(),
            "alignment": "369 • Φ • Fib",
            "design_count": 9,
            "families": families,
            "packs": [],
        }

        # Build per-family packs
        for fam in families:
            fam_dir = packs_dir / fam
            fam_dir.mkdir(parents=True, exist_ok=True)

            listing = _mk_listing(topic, fam)
            write_text(fam_dir / "LISTING_COPY.md", listing)
            artifacts.append(str(fam_dir / "LISTING_COPY.md"))

            # mockups (2 per family)
            mock_dir = fam_dir / "mockups"
            mock_dir.mkdir(parents=True, exist_ok=True)

            silhouettes = {
                "tshirt": "tee",
                "hoodie": "tee",
                "mug": "mug",
                "sticker": "sticker",
                "poster": "poster",
                "tote": "tote",
            }
            sil = silhouettes.get(fam, "tee")

            bg1 = (245, 245, 245)
            bg2 = (235, 240, 248)
            m1 = mock_dir / f"mockup_{fam}_01.png"
            m2 = mock_dir / f"mockup_{fam}_02.png"
            _make_mockup(bg1, f"{fam.upper()} • {topic}", preview_design, m1, sil)
            _make_mockup(bg2, f"{fam.upper()} • 369 • Φ • Fib", preview_design, m2, sil)
            artifacts.extend([str(m1), str(m2)])

            # copy over a small selection of designs for quick upload previews
            quick_dir = fam_dir / "quick_designs"
            quick_dir.mkdir(parents=True, exist_ok=True)
            for dn in ["design_01.png", "design_02.png", "design_03.png"]:
                src = designs_dir / dn
                if src.exists():
                    dst = quick_dir / dn
                    Image.open(src).save(dst)
                    artifacts.append(str(dst))

            manifest["packs"].append({"family": fam, "dir": str(fam_dir), "mockups": [str(m1), str(m2)]})

        (out_root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        artifacts.append(str(out_root / "manifest.json"))

        readme = (
            "# POD Superpack\n\n"
            "This folder contains:\n"
            "- designs/: 9 template designs (SVG + PNG)\n"
            "- packs/<family>/: per-product-family listing copy + mockups\n\n"
            "Recommended flow:\n"
            "1) Pick a family (tshirt/mug/sticker/etc)\n"
            "2) Use LISTING_COPY.md and mockups for the listing\n"
            "3) Upload your preferred design files from designs/\n\n"
            "Alignment: 369 • Φ • Fib\n"
        )
        write_text(out_root / "README.md", readme)
        artifacts.append(str(out_root / "README.md"))

        return ModuleResult(artifact_paths=artifacts, metadata={"out_root": str(out_root), "families": families})
