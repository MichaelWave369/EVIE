from __future__ import annotations
from typing import Any
import os, json
from .base import ModuleResult
from .utils import ensure_dir, write_text, write_json, now_iso, slugify
from .. import db

class StorefrontSiteBuilder:
    """Build a static multi-page storefront from the local product registry."""
    name = "storefront_site_builder"

    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        out_dir = f"{run_folder}/artifacts/{self.name}"
        site_dir = os.path.join(out_dir, "site")
        ensure_dir(site_dir)
        ensure_dir(os.path.join(site_dir, "products"))
        ensure_dir(os.path.join(site_dir, "assets"))

        products = db.list_products(limit=int(constraints.get("limit") or 200))
        write_json(os.path.join(site_dir, "products.json"), products)
        write_text(os.path.join(site_dir, "assets", "styles.css"), """body{font-family:Arial, sans-serif;max-width:980px;margin:30px auto;padding:0 16px;} .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;} .card{border:1px solid #ddd;border-radius:12px;padding:12px;} a{color:#0b5; text-decoration:none;} .muted{color:#666;}""")

        cards = []
        for p in products:
            ps = p.get("sku","")
            title = p.get("title","")
            cards.append(f"<div class='card'><div class='muted'>{ps}</div><h3><a href='products/{ps}.html'>{title}</a></h3><div>${int(p.get('price_cents',0))/100:.2f} • {p.get('tier','')}</div></div>")
            # product page
            html = f"""<!doctype html><html><head><meta charset='utf-8'/><link rel='stylesheet' href='../assets/styles.css'/><title>{title}</title></head>
<body><p><a href='../index.html'>← Back</a></p>
<h1>{title}</h1>
<p class='muted'>SKU: {ps} • Tier: {p.get('tier','')} • Price: ${int(p.get('price_cents',0))/100:.2f}</p>
<h2>What you get</h2>
<ul><li>Local-first bundle</li><li>Stamped proof-of-creation</li><li>Platform upload packs</li></ul>
<h2>Download</h2>
<p>Place your bundle zip at: <code>downloads/{ps}/content.zip</code></p>
<h2>FAQ</h2>
<p>No guarantees. Templates + guidance only.</p>
</body></html>"""
            write_text(os.path.join(site_dir, "products", f"{ps}.html"), html)

        index = f"""<!doctype html><html><head><meta charset='utf-8'/><link rel='stylesheet' href='assets/styles.css'/><title>{topic}</title></head>
<body><h1>{topic}</h1><p class='muted'>Local static storefront snapshot</p>
<div class='grid'>\n{''.join(cards)}\n</div></body></html>"""
        write_text(os.path.join(site_dir, "index.html"), index)

        return ModuleResult(name=self.name, artifacts=[os.path.join(site_dir, "index.html"), os.path.join(site_dir, "products.json")], summary={"products": len(products)})
