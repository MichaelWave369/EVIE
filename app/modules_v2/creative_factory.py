from __future__ import annotations
from typing import Any
from .base import ModuleResult
from .utils import write_text, write_json, ensure_dir

SVG_THUMB = """<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720">
<rect width="100%" height="100%" fill="#0b1020"/>
<text x="50%" y="50%" text-anchor="middle" font-family="Arial" font-size="56" fill="#e6f2ff">{text}</text>
</svg>"""

SVG_SQUARE = """<svg xmlns="http://www.w3.org/2000/svg" width="2000" height="2000">
<rect width="100%" height="100%" fill="#0b1020"/>
<text x="50%" y="48%" text-anchor="middle" font-family="Arial" font-size="72" fill="#e6f2ff">{text}</text>
<text x="50%" y="58%" text-anchor="middle" font-family="Arial" font-size="40" fill="#7ad7ff">369 • Φ • Fib</text>
</svg>"""

class CreativeFactory:
    name = "creative_factory"
    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        out_dir = f"{run_folder}/artifacts/{self.name}"
        ensure_dir(out_dir)
        thumbs=[]
        for i in range(1,10):
            p = f"{out_dir}/thumb_{i:02d}.svg"
            write_text(p, SVG_THUMB.format(text=f"{topic} • {i}"))
            thumbs.append(p)
        mockups=[]
        for i in range(1,13):
            p = f"{out_dir}/mockup_{i:02d}.svg"
            write_text(p, SVG_SQUARE.format(text=f"{topic} • mockup {i}"))
            mockups.append(p)
        write_json(f"{out_dir}/creative_manifest.json", {"thumbnails": thumbs, "mockups": mockups})
        return ModuleResult(name=self.name, artifacts=thumbs+mockups+[f"{out_dir}/creative_manifest.json"], summary={"thumbs": 9, "mockups": 12})
