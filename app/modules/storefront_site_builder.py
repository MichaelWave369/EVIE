
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List
import json
import datetime
import html

from app.modules.base import ModuleResult
from app.modules.base import BaseModule
from app.flywheel.slug import slugify
from app.settings import settings
from app.db import queries


def _money(cents: int | None) -> str:
    if cents is None:
        return ""
    try:
        return f"${(int(cents)/100.0):.2f}"
    except Exception:
        return ""


class StorefrontSiteBuilderModule(BaseModule):
    """
    Build a local static storefront site (multi-page, SKU routing).
    - index.html lists products
    - products/<SKU>.html pages for each product
    - assets/styles.css + products.json for client-side filtering
    Local-only: does not publish anything, only generates files.

    This is designed to work with the local Product Registry (SQLite) and your ./data/gumroad/<SKU>/ folders.
    """

    name = "storefront_site_builder"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        topic_slug = slugify(topic)
        out_root = Path(settings.data_dir) / "artifacts" / "storefront_site" / topic_slug
        site = out_root / "site"
        (site / "products").mkdir(parents=True, exist_ok=True)
        (site / "assets").mkdir(parents=True, exist_ok=True)

        limit = int(constraints.get("limit") or 500)
        base_path = constraints.get("base_path") or ""  # optional deployment base path hint
        title = constraints.get("title") or f"{topic} — Storefront"
        subtitle = constraints.get("subtitle") or "Local-first • 369 • Φ • Fib"

        products = queries.list_products(limit=limit)

        # Normalize product rows for a simple client-side index
        rows: List[Dict[str, Any]] = []
        for p in products:
            sku = (p.get("sku") or "").strip()
            if not sku:
                continue
            rows.append({
                "sku": sku,
                "name": p.get("name") or sku,
                "description": p.get("description") or "",
                "price_cents": int(p.get("price_cents") or 0),
                "price": _money(p.get("price_cents")),
                "status": p.get("status") or "draft",
                "current_version": p.get("current_version") or "",
                "updated_at": p.get("updated_at") or p.get("created_at") or "",
                "gumroad_dir": str(Path(settings.gumroad_dir) / sku),
                "tier": (p.get("metadata") or {}).get("tier", ""),
                "product_page": f"{base_path}products/{sku}.html".replace("//", "/"),
            })

        # Write products.json
        (site / "products.json").write_text(
            json.dumps({"generated_at": datetime.datetime.utcnow().isoformat(), "rows": rows}, indent=2),
            encoding="utf-8",
        )

        css = """
:root{
  --bg:#0b1020; --panel:#101a33; --ink:#eaf0ff; --muted:#a9b4d6;
  --accent:#35d0c7; --accent2:#ffb86b; --line:rgba(255,255,255,.08);
  --radius:18px;
}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;background:radial-gradient(1200px 800px at 20% -10%, rgba(53,208,199,.18), transparent 60%),radial-gradient(1200px 800px at 90% 10%, rgba(255,184,107,.12), transparent 60%),var(--bg);color:var(--ink);}
a{color:var(--accent);text-decoration:none}
.container{max-width:1100px;margin:0 auto;padding:24px}
.hero{padding:26px 18px;border:1px solid var(--line);background:linear-gradient(180deg, rgba(16,26,51,.9), rgba(16,26,51,.55));border-radius:var(--radius);box-shadow:0 10px 30px rgba(0,0,0,.28)}
.h1{font-size:34px;margin:0 0 6px}
.sub{color:var(--muted);margin:0}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:16px}
@media(max-width:980px){.grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:640px){.grid{grid-template-columns:1fr}}
.card{border:1px solid var(--line);background:rgba(16,26,51,.6);border-radius:var(--radius);padding:14px 14px 12px;display:flex;flex-direction:column;gap:8px}
.badges{display:flex;gap:8px;flex-wrap:wrap}
.badge{font-size:12px;padding:3px 8px;border-radius:999px;border:1px solid var(--line);color:var(--muted)}
.badge.accent{border-color:rgba(53,208,199,.45);color:var(--accent)}
.badge.gold{border-color:rgba(255,184,107,.45);color:var(--accent2)}
.title{font-weight:700;font-size:16px}
.desc{color:var(--muted);font-size:13px;line-height:1.35;min-height:34px}
.row{display:flex;justify-content:space-between;align-items:center;gap:10px}
.price{font-weight:800}
.search{width:100%;margin-top:14px;padding:10px 12px;border-radius:12px;border:1px solid var(--line);background:rgba(0,0,0,.15);color:var(--ink)}
.footer{margin-top:18px;color:var(--muted);font-size:12px}
hr{border:0;border-top:1px solid var(--line);margin:16px 0}
small{color:var(--muted)}
"""
        (site / "assets" / "styles.css").write_text(css.strip() + "\n", encoding="utf-8")

        index_html = """<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>__TITLE__</title>
  <link rel="stylesheet" href="assets/styles.css"/>
</head>
<body>
  <div class="container">
    <div class="hero">
      <div class="h1">__TITLE__</div>
      <p class="sub">__SUBTITLE__</p>
      <input id="q" class="search" placeholder="Search products (SKU, name, tier) …"/>
      <div class="grid" id="grid"></div>
      <div class="footer">
        Generated locally • 369 • Φ • Fib • __DATE__
      </div>
    </div>
  </div>

<script>
async function load(){
  const res = await fetch("products.json");
  const data = await res.json();
  const rows = data.rows || [];
  const grid = document.getElementById("grid");
  const q = document.getElementById("q");

  function render(filterText){
    const t = (filterText||"").toLowerCase();
    grid.innerHTML = "";
    rows
      .filter(r => !t || (r.sku+r.name+r.tier).toLowerCase().includes(t))
      .slice(0, 369)
      .forEach(r => {
        const el = document.createElement("div");
        el.className = "card";
        el.innerHTML = `
          <div class="badges">
            <span class="badge accent">${r.sku}</span>
            <span class="badge">${r.tier || "tier"}</span>
            <span class="badge gold">${r.price || ""}</span>
          </div>
          <div class="title">${r.name}</div>
          <div class="desc">${(r.description||"").slice(0,180)}${(r.description||"").length>180?"…":""}</div>
          <div class="row">
            <div><small>v${r.current_version || ""}</small></div>
            <a href="${r.product_page}">View →</a>
          </div>
        `;
        grid.appendChild(el);
      });
  }

  q.addEventListener("input", e => render(e.target.value));
  render("");
}
load();
</script>
</body>
</html>
"""
        index_html = index_html.replace("__TITLE__", html.escape(title))
        index_html = index_html.replace("__SUBTITLE__", html.escape(subtitle))
        index_html = index_html.replace("__DATE__", datetime.datetime.utcnow().strftime("%Y-%m-%d"))

        (site / "index.html").write_text(index_html, encoding="utf-8")

        # Product pages
        prod_tpl = """<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{title}</title>
  <link rel="stylesheet" href="../assets/styles.css"/>
</head>
<body>
  <div class="container">
    <div class="hero">
      <a href="../index.html">← Back</a>
      <div class="h1">{name}</div>
      <p class="sub">{sku} • {tier} • {price} • {version}</p>
      <hr/>
      <div class="desc">{desc}</div>
      <hr/>
      <div class="card">
        <div class="title">Download & Delivery</div>
        <div class="desc">
          This is a local-only generator. Upload your bundle ZIP to your chosen storefront.<br/>
          If you host downloads yourself, place the ZIP at: <code>downloads/{sku}/content.zip</code> and update links below.
        </div>
        <div class="row">
          <span class="price">{price}</span>
          <a href="{dl_link}">Download (placeholder) →</a>
        </div>
      </div>
      <div class="footer">
        369 • Φ • Fib • Generated locally • {ts}
      </div>
    </div>
  </div>
</body>
</html>
"""

        for r in rows:
            sku = r["sku"]
            name_ = html.escape(r["name"])
            desc = html.escape(r["description"] or "").replace("\n", "<br/>")
            page = prod_tpl.format(
                title=html.escape(f"{r['name']} — {sku}"),
                name=name_,
                sku=html.escape(sku),
                tier=html.escape(r.get("tier") or "tier"),
                price=html.escape(r.get("price") or ""),
                version=html.escape(r.get("current_version") or ""),
                desc=desc,
                dl_link=f"../downloads/{sku}/content.zip",
                ts=datetime.datetime.utcnow().isoformat(),
            )
            (site / "products" / f"{sku}.html").write_text(page, encoding="utf-8")

        readme = f"""# Static Storefront Site (Local Output)

This folder is generated locally by **storefront_site_builder**.

## What you get
- `index.html` — searchable product grid (up to 369 items)
- `products/<SKU>.html` — product detail pages
- `products.json` — product data used by the site
- `assets/styles.css` — simple theme

## How to deploy
Serve this `site/` folder as static files (any file host / static site host works).
Then place your downloadable ZIPs at a stable path, e.g.:

`downloads/<SKU>/content.zip`

and adjust the download link format if needed.

## Notes
- This generator is local-first; it does not publish, upload, or contact external services.
- Alignment: 369 • Φ • Fib
"""
        (site / "README.md").write_text(readme, encoding="utf-8")

        artifact_paths = [
            str(site / "index.html"),
            str(site / "products.json"),
            str(site / "assets" / "styles.css"),
            str(site / "README.md"),
        ]
        # Include a few product pages as artifacts for indexing
        for r in rows[:min(36, len(rows))]:
            artifact_paths.append(str(site / "products" / f"{r['sku']}.html"))

        return ModuleResult(
            artifact_paths=artifact_paths,
            metadata={
                "count_products": len(rows),
                "site_dir": str(site),
                "alignment": "369 • Φ • Fib",
            },
        )
