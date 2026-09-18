from __future__ import annotations
from typing import Any
from .base import ModuleResult
from .utils import write_text, write_json, ensure_dir, slugify

SVG_TMPL = """<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="1800">
<rect width="100%" height="100%" fill="white"/>
<text x="50%" y="45%" text-anchor="middle" font-family="Arial" font-size="72">{title}</text>
<text x="50%" y="55%" text-anchor="middle" font-family="Arial" font-size="42">369 • Φ • Fib</text>
</svg>"""

class PODSuperpack:
    name = "pod_superpack"
    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        out_dir = f"{run_folder}/artifacts/{self.name}"
        ensure_dir(out_dir)
        families = constraints.get("families") or ["tshirt","hoodie","mug","sticker","poster","tote"]
        designs=[]
        for i in range(1,10):
            title = f"{topic} #{i}"
            slug = slugify(title)
            path = f"{out_dir}/{slug}.svg"
            write_text(path, SVG_TMPL.format(title=title))
            designs.append({"title": title, "slug": slug, "svg": path})
        write_json(f"{out_dir}/designs.json", {"families": families, "designs": designs})
        write_text(f"{out_dir}/LISTING_COPY.md", f"# POD Listing Copy\n\n**Title:** {topic} (369 edition)\n\n**Bullets (6):**\n- Clean design\n- Local-first creator\n- 369/Φ/Fib aligned\n- Giftable\n- Minimal\n- Durable\n\n**Tags (9):**\n" + "\n".join([f"- tag{i}" for i in range(1,10)]))
        return ModuleResult(name=self.name, artifacts=[d["svg"] for d in designs] + [f"{out_dir}/designs.json", f"{out_dir}/LISTING_COPY.md"], summary={"designs": len(designs)})
