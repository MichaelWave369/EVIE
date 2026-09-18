from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Tuple
import json
from app.modules.base import ModuleResult, BaseModule
from app.export.packager import write_text
from app.flywheel.slug import slugify

def _safe_import_pillow():
    try:
        from PIL import Image, ImageDraw, ImageFont
        return Image, ImageDraw, ImageFont
    except Exception:
        return None

def _make_canvas(size: Tuple[int,int]):
    pillow = _safe_import_pillow()
    if not pillow:
        return None, None, None
    Image, ImageDraw, ImageFont = pillow
    img = Image.new("RGB", size, (18, 14, 28))
    return img, ImageDraw, ImageFont

def _load_font(ImageFont, size: int):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except Exception:
        return ImageFont.load_default()

def _draw_cover(title: str, subtitle: str, out_path: Path, size=(1600,2560)):
    pillow = _safe_import_pillow()
    if not pillow:
        return False
    Image, ImageDraw, ImageFont = pillow
    img = Image.new("RGB", size, (20, 16, 30))
    draw = ImageDraw.Draw(img)

    # simple gradient bands
    w,h=size
    for y in range(h):
        t = y / max(1,(h-1))
        r = int(20 + 40*t)
        g = int(16 + 28*t)
        b = int(30 + 60*t)
        draw.line([(0,y),(w,y)], fill=(r,g,b))

    # border
    draw.rectangle([40,40,w-40,h-40], outline=(220,180,120), width=6)

    # Title block
    font_title = _load_font(ImageFont, 88)
    font_sub = _load_font(ImageFont, 44)
    font_small = _load_font(ImageFont, 32)

    # Center title
    tw,th = draw.textbbox((0,0), title, font=font_title)[2:]
    draw.text(((w-tw)/2, 360), title, fill=(245,235,210), font=font_title)

    sw,sh = draw.textbbox((0,0), subtitle, font=font_sub)[2:]
    draw.text(((w-sw)/2, 520), subtitle, fill=(220,200,160), font=font_sub)

    # 369 / Phi / Fib signature
    sig = "369 • Φ • Fib"
    sigw,sigh = draw.textbbox((0,0), sig, font=font_small)[2:]
    draw.text(((w-sigw)/2, h-220), sig, fill=(220,180,120), font=font_small)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    return True

class BrandKitCoverFactoryModule(BaseModule):
    name = "brandkit_cover_factory"
    display_name = "Brand Kit + Cover Factory"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        title = constraints.get("title") or topic
        subtitle = constraints.get("subtitle") or "Local‑Only AI Vault • Passive Income Engine"

        out = Path("data/artifacts/brandkit") / slugify(topic)
        out.mkdir(parents=True, exist_ok=True)

        palette = {
            "ink": "#120E1C",
            "ember": "#E0B478",
            "paper": "#F5EBD2",
            "copper": "#B97A56",
            "teal": "#3BC9B6",
        }
        (out/"brand_palette.json").write_text(json.dumps(palette, indent=2), encoding="utf-8")

        style_guide = f"""# Brand Kit — {topic}

**Core rule:** 369 / Φ / Fibonacci alignment.

## Palette
- Ink: {palette['ink']}
- Ember: {palette['ember']}
- Paper: {palette['paper']}
- Copper: {palette['copper']}
- Teal: {palette['teal']}

## Typography
- Headlines: Bold, high-contrast
- Body: Clear, readable
- Signature: `369 • Φ • Fib`

## Assets generated
- KDP cover: `cover_kdp.png` (1600×2560)
- YouTube thumbnail: `thumbnail_youtube.png` (1280×720)
- Square listing: `square_listing.png` (2000×2000)
"""
        write_text(out/"style_guide.md", style_guide)

        created = []
        ok1 = _draw_cover(title, subtitle, out/"cover_kdp.png", size=(1600,2560))
        ok2 = _draw_cover(title, "YouTube Episode • 369 Loop", out/"thumbnail_youtube.png", size=(1280,720))
        ok3 = _draw_cover(title, "Digital Download", out/"square_listing.png", size=(2000,2000))

        if ok1: created.append(str(out/"cover_kdp.png"))
        if ok2: created.append(str(out/"thumbnail_youtube.png"))
        if ok3: created.append(str(out/"square_listing.png"))

        # If pillow missing, still generate text placeholders so pipeline doesn't break
        if not created:
            write_text(out/"README_NO_IMAGES.txt", "Pillow not installed. Install pillow to generate images: pip install pillow\n")

        paths = created + [str(out/"brand_palette.json"), str(out/"style_guide.md")]
        if not created:
            paths.append(str(out/"README_NO_IMAGES.txt"))

        return ModuleResult(
            artifact_paths=paths,
            metadata={"generated_images": bool(created), "palette": palette}
        )
