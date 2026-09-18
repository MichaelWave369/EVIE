from __future__ import annotations
from typing import Any
import os, json, html
from .base import ModuleResult
from .utils import ensure_dir, write_text, write_json, slugify, now_iso
from .. import db

def _read_text(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def _load_json(path: str) -> dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _esc(s: str) -> str:
    return html.escape(s or "")

def _platform_buy_placeholder(platform: str, sku: str) -> str:
    # Local-only: placeholders user can replace when publishing.
    key = platform.upper()
    return f"{{{{BUY_URL_{key}}}}}"

class LandingFinalizer:
    """Landing Finalizer + Proof Injection (local-only)

    Produces a single, clean landing page HTML that injects:
    - SKU / tier / price
    - buy buttons for each platform (placeholder URLs)
    - testimonial snippets from local DB (public consent only)
    - Phi bundle/cross-sell suggestions (from bundle_upsell_engine output)
    """
    name = "landing_finalizer"

    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int,
                 platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        tslug = slugify(topic)
        out_dir = os.path.join(run_folder, "artifacts", self.name, tslug)
        ensure_dir(out_dir)

        # Inputs
        lm_dir = os.path.join(run_folder, "artifacts", "lead_magnet_funnel_builder", tslug)
        base_html = _read_text(os.path.join(lm_dir, "LANDING_PAGE.html"))
        # Bundles / upsells
        upsells = _load_json(os.path.join(run_folder, "artifacts", "bundle_upsell_engine", "upsells.json"))

        # Testimonials (public only)
        max_t = int(constraints.get("max_testimonials") or 6)
        testimonials = db.list_testimonials(limit=max_t, sku=sku, public_only=True)

        # Choose bundle suggestions (prefer those that include current sku)
        bundles = upsells.get("bundles") or []
        rel_bundles = [b for b in bundles if sku in (b.get("items") or [])] or bundles
        max_b = int(constraints.get("max_bundles") or 3)
        rel_bundles = rel_bundles[:max_b]

        price_str = f"${price_cents/100:.2f}"
        platform_list = platforms or ["gumroad"]

        # Build testimonial HTML
        if testimonials:
            t_blocks = []
            for t in testimonials:
                who = (t.get("name") or "Anonymous").strip()
                role = (t.get("role") or "").strip()
                rating = t.get("rating")
                head = _esc(who) + (f" — {_esc(role)}" if role else "")
                stars = ""
                if rating:
                    stars = " " + ("★" * max(0, min(5, int(rating))))
                t_blocks.append(f"""<blockquote class="t">
  <div class="t-head">{head}{stars}</div>
  <div class="t-body">{_esc((t.get("text") or "").strip())}</div>
</blockquote>""")
            testimonials_html = "\n".join(t_blocks)
        else:
            testimonials_html = """<div class="placeholder">
  <p><strong>Social proof goes here.</strong> Add 3–6 short testimonials once you have early users.</p>
  <ul>
    <li>What changed for them?</li>
    <li>What was the fastest win?</li>
    <li>Who is this perfect for?</li>
  </ul>
</div>"""

        # Build bundle HTML
        if rel_bundles:
            b_cards=[]
            for b in rel_bundles:
                items = ", ".join(b.get("items") or [])
                b_sku = b.get("bundle_sku") or "BUNDLE"
                b_price = (int(b.get("phi_bundle_price_cents") or 0))/100.0
                disc = b.get("discount_pct")
                buy = f"{{{{BUY_URL_BUNDLE_{_esc(b_sku).replace('-','_')}}}}}"
                b_cards.append(f"""<div class="bundle-card">
  <div class="bundle-title">{_esc(b_sku)}</div>
  <div class="bundle-items">{_esc(items)}</div>
  <div class="bundle-price">${b_price:.2f} <span class="bundle-disc">({disc}% off)</span></div>
  <a class="buy secondary" href="{buy}">Bundle link placeholder</a>
</div>""")
            bundles_html="\n".join(b_cards)
        else:
            bundles_html = """<div class="placeholder">
  <p><strong>Bundle suggestions will appear here</strong> once your catalog has multiple SKUs.</p>
</div>"""

        # Buy buttons
        buy_buttons="\n".join([
            f'<a class="buy" href="{_platform_buy_placeholder(p, sku)}">Buy on {p.upper()}</a>'
            for p in platform_list
        ])

        # Final HTML (simple, readable, local-friendly)
        final_html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{_esc(topic)} — {sku}</title>
  <style>
    :root {{
      --bg: #0b1020;
      --card: #121a33;
      --text: #e8ecff;
      --muted: #b8c1ff;
      --accent: #40e0d0;
      --accent2: #d38bff;
      --line: rgba(255,255,255,0.10);
    }}
    body {{ margin:0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; background: var(--bg); color: var(--text); }}
    .wrap {{ max-width: 1100px; margin: 0 auto; padding: 36px 20px; }}
    .hero {{ display: grid; grid-template-columns: 1fr; gap: 18px; padding: 24px; border: 1px solid var(--line); border-radius: 18px; background: linear-gradient(180deg, rgba(64,224,208,0.08), rgba(211,139,255,0.06)); }}
    .kicker {{ color: var(--muted); letter-spacing: 0.08em; text-transform: uppercase; font-size: 12px; }}
    h1 {{ margin: 0; font-size: 34px; line-height: 1.1; }}
    .meta {{ display:flex; flex-wrap:wrap; gap:10px; color: var(--muted); font-size: 14px; }}
    .pill {{ border:1px solid var(--line); padding:6px 10px; border-radius: 999px; background: rgba(255,255,255,0.03); }}
    .cta {{ display:flex; flex-wrap:wrap; gap:10px; margin-top: 10px; }}
    a.buy {{ display:inline-block; padding: 12px 14px; border-radius: 12px; background: var(--accent); color: #001018; text-decoration:none; font-weight: 700; }}
    a.buy.secondary {{ background: rgba(255,255,255,0.08); color: var(--text); border: 1px solid var(--line); }}
    .grid {{ display:grid; gap: 16px; margin-top: 18px; }}
    @media (min-width: 980px) {{
      .grid {{ grid-template-columns: 1.618fr 1fr; }}
      .hero {{ grid-template-columns: 1.618fr 1fr; align-items: center; }}
    }}
    .card {{ padding: 18px; border-radius: 18px; border: 1px solid var(--line); background: var(--card); }}
    h2 {{ margin: 0 0 10px 0; font-size: 18px; }}
    p {{ margin: 8px 0; color: var(--muted); }}
    ul {{ margin: 8px 0 0 18px; color: var(--muted); }}
    .t {{ margin: 0 0 12px 0; padding: 12px 12px; border-radius: 14px; border: 1px solid var(--line); background: rgba(255,255,255,0.03); }}
    .t-head {{ font-weight: 700; color: var(--text); margin-bottom: 6px; }}
    .t-body {{ color: var(--muted); }}
    .bundle-card {{ padding: 12px; border-radius: 14px; border: 1px solid var(--line); background: rgba(255,255,255,0.03); margin-bottom: 10px; }}
    .bundle-title {{ font-weight: 800; }}
    .bundle-items, .bundle-price {{ color: var(--muted); margin-top: 4px; }}
    .bundle-disc {{ color: var(--accent2); }}
    .foot {{ margin-top: 18px; color: var(--muted); font-size: 12px; opacity: 0.9; }}
    .placeholder {{ color: var(--muted); }}
    .hr {{ height:1px; background: var(--line); margin: 12px 0; }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div>
        <div class="kicker">369 • Φ • Fib aligned • local-first</div>
        <h1>{_esc(topic)}</h1>
        <div class="meta">
          <span class="pill">SKU: {_esc(sku)}</span>
          <span class="pill">Tier: {_esc(tier)}</span>
          <span class="pill">Price: {price_str}</span>
          <span class="pill">Generated: {now_iso()}</span>
        </div>
        <div class="cta">
          {buy_buttons}
          <a class="buy secondary" href="{{{{TESTIMONIAL_FORM_URL}}}}">Leave a testimonial</a>
        </div>
        <div class="hr"></div>
        <p><strong>What this is:</strong> a self-contained product pack built to help your audience get a fast win — and help you sell it repeatedly.</p>
        <p><strong>How it’s structured:</strong> 3 pillars → 6 deliverables → 9 touchpoints (Fib cadence).</p>
      </div>
      <div class="card">
        <h2>Hero media placeholder</h2>
        <p>Drop an image here later: <code>hero.png</code> or a screenshot collage.</p>
        <p>Optional: include a 30–60 sec demo clip thumbnail.</p>
      </div>
    </section>

    <div class="grid">
      <section class="card">
        <h2>Social Proof</h2>
        {testimonials_html}
      </section>

      <section class="card">
        <h2>Bundles + Cross‑Sells (Φ pricing)</h2>
        {bundles_html}
        <div class="hr"></div>
        <p><strong>Order bump idea:</strong> add a “Quickstart + Checklist Pack” at ~0.382 of core price.</p>
      </section>
    </div>

    <section class="card" style="margin-top:16px;">
      <h2>Notes for publishing (placeholders)</h2>
      <ul>
        <li>Replace <code>{{BUY_URL_PLATFORM}}</code> placeholders with real links per platform.</li>
        <li>Replace <code>{{TESTIMONIAL_FORM_URL}}</code> with your local form URL (or a hosted form later).</li>
        <li>Keep testimonials to 1–2 sentences each (clarity converts).</li>
      </ul>
      <div class="foot">
        Local-only generator. No external calls. Proof + fingerprints are stamped in the run folder.
      </div>
    </section>

    <!-- Base landing HTML (optional) preserved below for reference -->
    <section class="card" style="margin-top:16px;">
      <h2>Source Landing (reference)</h2>
      <p>This section preserves the earlier landing HTML (if present). You can delete it before publishing.</p>
      <div class="hr"></div>
      <div style="color:var(--muted); font-size: 13px; white-space: pre-wrap;">{_esc(base_html)[:6000]}</div>
    </section>

  </div>
</body>
</html>
"""

        html_path = os.path.join(out_dir, "FINAL_LANDING_PAGE.html")
        write_text(html_path, final_html)

        md_lines = [
            f"# {_esc(topic)} — Landing",
            "",
            f"**SKU:** {sku}",
            f"**Tier:** {tier}",
            f"**Price:** {price_str}",
            "",
            "## Buy buttons (placeholders)",
        ]
        for p in platform_list:
            md_lines.append(f"- {p.upper()}: {{{{BUY_URL_{p.upper()}}}}}")
        md_lines += ["", "## Social proof", ""]
        if testimonials:
            for t in testimonials:
                who=(t.get("name") or "Anonymous").strip()
                role=(t.get("role") or "").strip()
                rating=t.get("rating")
                head=f"{who}" + (f" — {role}" if role else "") + (f" ({rating}/5)" if rating else "")
                md_lines.append(f"> **{head}**\n> {(t.get('text') or '').strip()}\n")
        else:
            md_lines.append("> (Add testimonials here once you have early users.)")
        md_lines += ["", "## Bundles (Φ pricing)", ""]
        if rel_bundles:
            for b in rel_bundles:
                md_lines.append(f"- **{b.get('bundle_sku')}** — {', '.join(b.get('items') or [])} → ${int(b.get('phi_bundle_price_cents') or 0)/100:.2f} ({b.get('discount_pct')}% off)")
        else:
            md_lines.append("- (No bundles yet — add more SKUs to generate suggestions.)")

        md_path = os.path.join(out_dir, "FINAL_LANDING_PAGE.md")
        write_text(md_path, "\n".join(md_lines) + "\n")

        manifest = {
            "module": self.name,
            "created_at": now_iso(),
            "topic": topic,
            "sku": sku,
            "tier": tier,
            "price_cents": price_cents,
            "platforms": platform_list,
            "testimonials_used": len(testimonials),
            "bundles_used": len(rel_bundles),
        }
        man_path = os.path.join(out_dir, "MANIFEST.json")
        write_json(man_path, manifest)

        return ModuleResult(
            name=self.name,
            artifacts=[
                os.path.relpath(html_path, run_folder),
                os.path.relpath(md_path, run_folder),
                os.path.relpath(man_path, run_folder),
            ],
            summary=manifest
        )
