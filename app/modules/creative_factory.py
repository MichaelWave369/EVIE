
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List, Tuple
import datetime, json, random

from PIL import Image, ImageDraw, ImageFont

from app.modules.base import ModuleResult
from app.settings import settings
from app.export.packager import write_text
from app.flywheel.slug import slugify

def _safe_font(size: int):
    # Pillow default bitmap font fallback is fine for local placeholder visuals.
    try:
        return ImageFont.truetype("arial.ttf", size=size)
    except Exception:
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size=size)
        except Exception:
            return ImageFont.load_default()

def _palette() -> Dict[str, str]:
    # EmberVault-ish: deep navy / crystalline teal / rose-copper
    return {
        "bg": "#071423",
        "panel": "#0B2338",
        "accent": "#29D3C7",
        "warm": "#C07B6A",
        "text": "#EAF2FF",
        "muted": "#9DB2C7",
    }

def _make_image(size: Tuple[int,int], title: str, subtitle: str, footer: str, variant: int) -> Image.Image:
    w, h = size
    pal = _palette()
    img = Image.new("RGB", (w, h), pal["bg"])
    d = ImageDraw.Draw(img)

    # Panels (simple phi-ish proportions)
    margin = int(min(w,h) * 0.05)
    panel_w = int((w - 2*margin) * 0.618)
    panel_h = int((h - 2*margin) * 0.382)
    # main hero panel
    d.rounded_rectangle([margin, margin, w - margin, h - margin], radius=int(min(w,h)*0.03), outline=pal["accent"], width=4)
    d.rounded_rectangle([margin, margin, margin + panel_w, margin + panel_h], radius=int(min(w,h)*0.02), fill=pal["panel"])
    # side strip
    d.rounded_rectangle([margin + panel_w + int(margin*0.6), margin, w - margin, margin + panel_h], radius=int(min(w,h)*0.02), fill="#0E2B45")

    # Text
    t_font = _safe_font(int(h*0.06))
    s_font = _safe_font(int(h*0.035))
    f_font = _safe_font(int(h*0.028))

    d.text((margin + int(margin*0.8), margin + int(margin*0.6)), title, font=t_font, fill=pal["text"])
    d.text((margin + int(margin*0.8), margin + int(margin*0.6) + int(h*0.08)), subtitle, font=s_font, fill=pal["muted"])
    d.text((margin + int(margin*0.8), h - margin - int(h*0.05)), footer, font=f_font, fill=pal["warm"])

    # 369 stamp
    stamp = f"369 • Φ • Fib  |  v{variant:02d}"
    d.text((w - margin - int(w*0.35), h - margin - int(h*0.05)), stamp, font=f_font, fill=pal["accent"])
    return img

def _write_png(path: Path, img: Image.Image) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG")

class CreativeFactoryModule:
    name = "creative_factory"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        key = slugify(topic)
        out_dir = Path(settings.data_dir) / "artifacts" / "creative_factory" / key
        out_dir.mkdir(parents=True, exist_ok=True)

        brand = {
            "palette": _palette(),
            "rules": {
                "alignment": "369 • Φ • Fib",
                "thumbnail_variants": 9,
                "mockups": 12,
                "watermark": True,
            },
            "generated_at": datetime.datetime.utcnow().isoformat(),
        }
        write_text(out_dir / "brand_visuals.json", json.dumps(brand, indent=2))

        # 12 mockups (square)
        mockups = []
        for i in range(1, 13):
            img = _make_image((2000, 2000), topic, "Mockup / Listing Visual", "Local-only • EmberVault Income Engine", i)
            p = out_dir / "mockups" / f"mockup_{i:02d}.png"
            _write_png(p, img)
            mockups.append(str(p))

        # 9 thumbnails (16:9)
        thumbs = []
        for i in range(1, 10):
            img = _make_image((1280, 720), topic, "Thumbnail Variant", "3 / 6 / 9 hooks • Φ pacing", i)
            p = out_dir / "thumbnails" / f"thumb_{i:02d}.png"
            _write_png(p, img)
            thumbs.append(str(p))

        # watermark (simple SVG)
        watermark_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="260">
  <rect width="100%" height="100%" fill="{_palette()['bg']}"/>
  <text x="50" y="160" font-size="72" fill="{_palette()['accent']}" font-family="Arial, DejaVu Sans">369 • Φ • Fib</text>
  <text x="50" y="220" font-size="32" fill="{_palette()['muted']}" font-family="Arial, DejaVu Sans">EmberVault • Local-only</text>
</svg>"""
        wm_path = out_dir / "watermarks" / "watermark_369_phi_fib.svg"
        write_text(wm_path, watermark_svg)

        manifest = {
            "topic": topic,
            "outputs": {
                "mockups": 12,
                "thumbnails": 9,
                "watermark": str(wm_path),
            },
            "folders": {
                "mockups": str(out_dir / "mockups"),
                "thumbnails": str(out_dir / "thumbnails"),
                "watermarks": str(out_dir / "watermarks"),
            },
        }
        write_text(out_dir / "MANIFEST.json", json.dumps(manifest, indent=2))

        paths = [str(out_dir / "brand_visuals.json"), str(out_dir / "MANIFEST.json"), str(wm_path)] + mockups + thumbs
        return ModuleResult(artifact_paths=paths, metadata={"module": self.name, "mockups": 12, "thumbnails": 9})
