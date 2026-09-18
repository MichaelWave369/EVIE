from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Tuple
import datetime
import json
import re

from PIL import Image, ImageDraw, ImageFont

from app.modules.base import ModuleResult
from app.settings import settings
from app.flywheel.slug import slugify
from app.export.packager import write_text


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-zA-Z0-9\- ]+", " ", s or "")).strip()


def _default_phrases(topic: str) -> List[str]:
    base = _clean(topic)
    if len(base) > 54:
        base = base[:54].rstrip()
    # 9 variants, 3 families
    a = [
        f"{base}",
        f"{base} • 369",
        f"{base} • Φ",
    ]
    b = [
        f"Local-First • {base}",
        f"369 • Φ • Fib • {base}",
        f"Build • Ship • Iterate • {base}",
    ]
    c = [
        f"EmberVault • {base}",
        f"Sovereign Systems • {base}",
        f"Focus • Flow • Fortune • {base}",
    ]
    return (a + b + c)[:9]


def _watermark_text(sku: str = "EV369") -> str:
    return f"{sku} | 369 • Φ • Fib"


def _make_svg(text: str, size: Tuple[int, int], stamp: str) -> str:
    w, h = size
    # Minimal, printable SVG (vector text). Buyers can edit in Inkscape.
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        f"<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{w}\" height=\"{h}\" viewBox=\"0 0 {w} {h}\">\n"
        "  <rect width=\"100%\" height=\"100%\" fill=\"none\"/>\n"
        f"  <text x=\"50%\" y=\"48%\" text-anchor=\"middle\" font-family=\"Arial\" font-size=\"{int(min(w,h)*0.055)}\" fill=\"black\">{text}</text>\n"
        f"  <text x=\"50%\" y=\"55%\" text-anchor=\"middle\" font-family=\"Arial\" font-size=\"{int(min(w,h)*0.030)}\" fill=\"black\">{stamp}</text>\n"
        "</svg>\n"
    )


def _make_png(text: str, size: Tuple[int, int], stamp: str, out_path: Path) -> None:
    w, h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Fonts: default for portability
    f_big = ImageFont.load_default()
    f_small = ImageFont.load_default()

    # Centered text with simple wrapping
    main = text
    sub = stamp

    # Calculate approximate positions
    y_main = int(h * 0.45)
    y_sub = int(h * 0.54)

    def _centered(draw, s, y, fill, font):
        bbox = draw.textbbox((0, 0), s, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (w - tw) // 2
        draw.text((x, y - th // 2), s, fill=fill, font=font)

    # Add a faint outline for readability
    def _stroke(draw, s, y, font):
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            bbox = draw.textbbox((0, 0), s, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            x = (w - tw) // 2
            draw.text((x+dx, y - th//2 + dy), s, fill=(0,0,0,90), font=font)

    _stroke(d, main, y_main, f_big)
    _centered(d, main, y_main, (0, 0, 0, 255), f_big)

    _stroke(d, sub, y_sub, f_small)
    _centered(d, sub, y_sub, (0, 0, 0, 255), f_small)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)


class PODPackGeneratorModule:
    """Print-on-demand pack generator.

    Generates 9 designs (SVG + PNG by default) plus listing copy and a print manifest.
    This is intentionally local-only and template-driven.
    """

    name = "pod_pack_generator"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        key = slugify(topic)
        out_root = Path(settings.data_dir) / "artifacts" / "pod_pack" / key
        designs_dir = out_root / "designs"
        listings_dir = out_root / "listings"
        designs_dir.mkdir(parents=True, exist_ok=True)
        listings_dir.mkdir(parents=True, exist_ok=True)

        size = constraints.get("size") or [4500, 5400]
        w, h = int(size[0]), int(size[1])

        phrases = constraints.get("phrases")
        if isinstance(phrases, str):
            phrases = [p.strip() for p in phrases.split("\n") if p.strip()]
        phrase_list = list(phrases) if phrases else _default_phrases(topic)
        phrase_list = (phrase_list + _default_phrases(topic))[:9]

        sku_hint = str(constraints.get("sku") or f"EV369-{key}")
        stamp = _watermark_text(sku_hint)

        formats = constraints.get("formats") or ["svg", "png"]
        formats = [f.lower() for f in formats]

        manifest: Dict[str, Any] = {
            "module": self.name,
            "topic": topic,
            "created_at": datetime.datetime.utcnow().isoformat(),
            "alignment": "369 • Φ • Fib",
            "size": {"width": w, "height": h},
            "formats": formats,
            "designs": [],
        }

        artifacts: List[str] = []

        for i, text in enumerate(phrase_list, start=1):
            design_id = f"design_{i:02d}"
            entry = {"id": design_id, "text": text, "files": []}

            if "svg" in formats:
                svg = _make_svg(text=text, size=(w, h), stamp=stamp)
                svg_path = designs_dir / f"{design_id}.svg"
                write_text(svg_path, svg)
                entry["files"].append(str(svg_path))
                artifacts.append(str(svg_path))

            if "png" in formats:
                png_path = designs_dir / f"{design_id}.png"
                _make_png(text=text, size=(w, h), stamp=stamp, out_path=png_path)
                entry["files"].append(str(png_path))
                artifacts.append(str(png_path))

            manifest["designs"].append(entry)

        # Listing copy (3/6/9)
        listing_md = (
            "# Print-on-Demand Listing Copy\n\n"
            f"**Product theme:** {topic}\n\n"
            "## 3-line hook\n"
            "- Minimal, clean designs you can use for shirts/posters/stickers.\n"
            "- Built with a consistent 369 • Φ • Fib signature.\n"
            "- Delivered as high-res PNG + editable SVG (local-first).\n\n"
            "## 6 bullet benefits\n"
            "- 9 designs (3 families × 3 variations)\n"
            "- Print-ready resolution defaults (4500×5400)\n"
            "- SVG versions included for easy editing\n"
            "- Consistent branding stamp + watermark text\n"
            "- Works for tees, posters, stickers, mugs (resize as needed)\n"
            "- Organized folders + manifest for quick uploading\n\n"
            "## 9 keywords\n"
            "- 369\n- phi\n- fibonacci\n- local-first\n- minimalist\n- motivational\n- creator\n- systems\n- productivity\n\n"
            "---\n"
            "**Note:** This pack is generated as a template. Review and customize before selling.\n"
        )
        write_text(listings_dir / "LISTING_COPY.md", listing_md)
        artifacts.append(str(listings_dir / "LISTING_COPY.md"))

        (out_root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        artifacts.append(str(out_root / "manifest.json"))

        write_text(
            out_root / "README.md",
            "# POD Pack (Local)\n\n"
            "This folder contains print-on-demand ready design files.\n\n"
            "- designs/: SVG + PNG\n"
            "- listings/: listing copy and keywords\n"
            "- manifest.json: structured file map\n\n"
            "Alignment: 369 • Φ • Fib\n",
        )
        artifacts.append(str(out_root / "README.md"))

        return ModuleResult(artifact_paths=artifacts, metadata={"out_root": str(out_root), "count": 9, "size": [w, h]})
