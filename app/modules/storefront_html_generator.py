
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Optional
import datetime, json

from app.modules.base import ModuleResult
from app.settings import settings
from app.flywheel.slug import slugify
from app.export.packager import write_text
from app.rag.llm import LLM

def _read_optional(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return None

def _basic_css() -> str:
    return """:root{
  --bg:#0b1020; --card:#111a33; --ink:#e9f0ff; --muted:#b6c3e6; --accent:#4ee6d9; --accent2:#f2b3a6;
  --r:18px;
}
*{box-sizing:border-box}
body{margin:0;font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial;background:radial-gradient(1200px 800px at 20% 10%, #132252 0%, var(--bg) 60%);color:var(--ink);line-height:1.45}
a{color:var(--accent)}
.wrap{max-width:1100px;margin:0 auto;padding:24px}
.hero{display:grid;grid-template-columns:1.2fr .8fr;gap:24px;align-items:stretch}
.card{background:linear-gradient(180deg,var(--card),#0b1226);border:1px solid rgba(255,255,255,.08);border-radius:var(--r);padding:18px;box-shadow:0 12px 30px rgba(0,0,0,.35)}
.kicker{letter-spacing:.18em;text-transform:uppercase;color:var(--muted);font-size:12px}
h1{margin:10px 0 8px;font-size:40px}
h2{margin:0 0 10px;font-size:22px}
p{margin:8px 0;color:var(--muted)}
.grid369{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.badge{display:inline-block;padding:6px 10px;border-radius:999px;background:rgba(78,230,217,.12);border:1px solid rgba(78,230,217,.22);color:var(--accent);font-size:12px}
.cta{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}
.btn{padding:12px 14px;border-radius:14px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.06);color:var(--ink);text-decoration:none}
.btn.primary{background:linear-gradient(135deg,var(--accent),#7aa6ff);border:none;color:#081022}
.small{font-size:12px;color:rgba(233,240,255,.72)}
.footer{margin-top:30px;padding-top:18px;border-top:1px solid rgba(255,255,255,.08);color:rgba(233,240,255,.66)}
@media(max-width:900px){.hero{grid-template-columns:1fr}.grid369{grid-template-columns:1fr}}
"""

def _fallback_copy(topic: str) -> Dict[str, Any]:
    return {
        "headline": f"{topic}",
        "subhead": "Local-first, consent-gated, 369/Φ/Fib aligned income engine.",
        "bullets": [
            "Generate sellable assets: ebooks, courses, templates, videos, POD packs, SEO pages",
            "Auto-package listings for multiple platforms (KDP/Etsy/Gumroad/YouTube/Udemy/Unity/Fab)",
            "Create funnels, emails, memberships, and programmatic SEO at scale",
            "QA gates + A/B kits + metrics loop to improve over time",
            "Licensing + stamping + proof-of-creation built in (local only)",
            "Factory queue to generate 9-SKU product lines automatically",
        ],
        "cta_primary": "Download Bundle",
        "cta_secondary": "View Contents",
        "price": "$29–$99 (starter) / $199+ (pro licensing)",
        "disclaimer": "Draft content. Review for compliance and accuracy before publishing.",
    }

class StorefrontHTMLGeneratorModule:
    name = "storefront_html_generator"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        slug = slugify(topic)
        out_dir = settings.data_dir / "artifacts" / "storefront" / slug
        out_dir.mkdir(parents=True, exist_ok=True)

        copy = _fallback_copy(topic)

        # Optional LLM refinement
        try:
            llm = LLM.from_settings()
            if llm.backend != "none" and bool(constraints.get("llm_refine", True)):
                prompt = (
                    "Create a storefront copy pack for a digital bundle. Return JSON with keys: "
                    "headline, subhead, bullets (6), cta_primary, cta_secondary, price, disclaimer. "
                    "Keep it truthful and avoid guarantees. Use 3/6/9 rhythm in wording.\n\n"
                    f"Topic: {topic}"
                )
                raw = llm.chat([
                    {"role":"system","content":"You write high-converting but honest landing copy."},
                    {"role":"user","content":prompt},
                ])
                try:
                    j = json.loads(raw)
                    if isinstance(j, dict) and "headline" in j:
                        copy.update(j)
                except Exception:
                    pass
        except Exception:
            pass

        # If a bundle plan exists from bundle_assembler, link it
        bundle_plan = out_dir.parent.parent / "bundle_assembler" / slug / "bundle_plan.json"
        plan_json = None
        if bundle_plan.exists():
            try:
                plan_json = json.loads(bundle_plan.read_text(encoding="utf-8"))
            except Exception:
                plan_json = None

        html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{copy['headline']}</title>
  <link rel="stylesheet" href="./styles.css" />
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <div class="card">
        <div class="kicker">Phi369 • Local Only • Vault + RAG</div>
        <h1>{copy['headline']}</h1>
        <p>{copy['subhead']}</p>
        <div class="cta">
          <a class="btn primary" href="#download">{copy['cta_primary']}</a>
          <a class="btn" href="#contents">{copy['cta_secondary']}</a>
          <span class="badge">{copy['price']}</span>
        </div>
        <p class="small">{copy['disclaimer']}</p>
      </div>
      <div class="card">
        <h2>369 Value Grid</h2>
        <div class="grid369">
          <div class="card"><span class="badge">3 Pillars</span><p>Create • Distribute • Compound</p></div>
          <div class="card"><span class="badge">6 Loops</span><p>Research → Build → Package → Convert → Deliver → Optimize</p></div>
          <div class="card"><span class="badge">9 Outputs</span><p>One topic becomes a constellation of sellable assets</p></div>
        </div>
      </div>
    </div>

    <div class="card" id="contents" style="margin-top:18px">
      <h2>What’s inside</h2>
      <ul>
        {''.join([f'<li>{b}</li>' for b in copy['bullets'][:6]])}
      </ul>
      {('<p class="small">Bundle Plan detected: ' + str(len(plan_json.get('skus',[]))) + ' SKUs ready.</p>') if plan_json else '<p class="small">Tip: run bundle_assembler to generate a 9‑SKU line, then regenerate this storefront.</p>'}
    </div>

    <div class="card" id="download" style="margin-top:18px">
      <h2>Download / Upload</h2>
      <p>EmberVault exports a folder you can upload to your storefronts. Nothing is pushed automatically unless you choose.</p>
      <p class="small">Recommended: upload <code>content.zip</code> plus <code>LISTING_COPY.md</code> and the platform checklists.</p>
    </div>

    <div class="footer">
      <div>Generated locally • {datetime.datetime.utcnow().date().isoformat()} • 369 / Φ / Fib aligned</div>
    </div>
  </div>
</body>
</html>
"""

        write_text(out_dir / "index.html", html)
        write_text(out_dir / "styles.css", _basic_css())
        write_text(out_dir / "product.json", json.dumps({"topic": topic, "generated_at": datetime.datetime.utcnow().isoformat()+"Z", "copy": copy}, indent=2))
        write_text(out_dir / "upsells.json", json.dumps({"suggested": ["bundle_assembler", "membership_automation", "pod_superpack", "programmatic_seo_generator"]}, indent=2))

        return ModuleResult(
            artifact_paths=[str(out_dir / "index.html"), str(out_dir / "styles.css"), str(out_dir / "product.json")],
            metadata={"bundle_plan_detected": bool(plan_json)}
        )
