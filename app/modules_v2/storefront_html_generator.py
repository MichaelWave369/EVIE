from __future__ import annotations
from typing import Any
from .base import ModuleResult
from .utils import write_text, write_json, ensure_dir
from .. import db

HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>{title}</title><style>
body{{font-family:Arial;margin:24px;max-width:960px}}
.card{{border:1px solid #ddd;border-radius:12px;padding:16px;margin:12px 0}}
.small{{color:#666}}
</style></head>
<body>
<h1>{title}</h1>
<p class="small">Local-generated storefront page. Replace download links with your hosting location.</p>
{cards}
</body></html>"""

class StorefrontHTMLGenerator:
    name = "storefront_html_generator"
    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        out_dir = f"{run_folder}/artifacts/{self.name}"
        ensure_dir(out_dir)
        prods = db.list_products()
        cards=[]
        for p in prods[:12]:
            cards.append(f"<div class='card'><h2>{p['title']}</h2><div class='small'>SKU: {p['sku']} • Tier: {p['tier']} • ${p['price_cents']/100:.2f}</div><p><a href='downloads/{p['sku']}/content.zip'>Download</a></p></div>")
        html = HTML.format(title="Storefront", cards="\n".join(cards) if cards else "<p>No products yet. Build an offer first.</p>")
        write_text(f"{out_dir}/index.html", html)
        write_json(f"{out_dir}/products_snapshot.json", {"count": len(prods)})
        return ModuleResult(name=self.name, artifacts=[f"{out_dir}/index.html", f"{out_dir}/products_snapshot.json"], summary={"products": len(prods)})
