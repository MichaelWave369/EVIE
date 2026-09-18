from __future__ import annotations
from typing import Any
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from .base import ModuleResult
from .utils import ensure_dir, write_text, write_json, slugify, three_six_nine_sections, FIB, now_iso

class LeadMagnetFunnelBuilder:
    """Local-first lead magnet + landing + email drip + upsell pack.

    Goal: turn one core idea into a full funnel surface without any external services.
    """

    name = "lead_magnet_funnel_builder"

    def _make_pdf(self, pdf_path: str, title: str, sections: list[tuple[str, list[str]]]):
        ensure_dir(os.path.dirname(pdf_path))
        c = canvas.Canvas(pdf_path, pagesize=letter)
        width, height = letter
        x = 72
        y = height - 72

        c.setFont("Helvetica-Bold", 18)
        c.drawString(x, y, title)
        y -= 28

        c.setFont("Helvetica", 11)
        c.drawString(x, y, f"Generated locally • {now_iso()} • 369/Φ/Fib aligned")
        y -= 18

        for heading, bullets in sections:
            if y < 120:
                c.showPage(); y = height - 72
            c.setFont("Helvetica-Bold", 14)
            c.drawString(x, y, heading)
            y -= 18
            c.setFont("Helvetica", 11)
            for b in bullets:
                if y < 90:
                    c.showPage(); y = height - 72
                    c.setFont("Helvetica", 11)
                c.drawString(x + 12, y, f"• {b}")
                y -= 14
            y -= 10

        c.showPage()
        c.save()

    def generate(
        self,
        *,
        topic: str,
        run_folder: str,
        sku: str,
        tier: str,
        price_cents: int,
        platforms: list[str],
        constraints: dict[str, Any],
    ) -> ModuleResult:
        tslug = slugify(topic)
        out_dir = os.path.join(run_folder, "artifacts", self.name, tslug)
        ensure_dir(out_dir)

        # Inputs
        audience = constraints.get("audience") or "people who want a practical, local-first system"
        promise = constraints.get("promise") or "A simple, repeatable way to go from idea → sellable pack"
        lead_title = constraints.get("lead_title") or f"{topic} — Quickstart Kit (369)"
        upsell_title = constraints.get("upsell_title") or f"{topic} — Complete Collection (Φ Bundle)"
        primary_cta = constraints.get("cta") or "Download the free Quickstart"

        bullets3 = [
            "Clarity: define the one problem you solve",
            "Delivery: ship a usable artifact (not a vibe)",
            "Compounding: reuse outputs into the next layer",
        ]
        bullets6 = [
            "Lead magnet (free) — simple + fast win",
            "Landing page copy (A/B ready)",
            "Email drip sequence (Fib cadence)",
            "Upsell page copy (Core/Premium)",
            "Order bump idea + FAQ",
            "Tracking checklist (what to measure)",
        ]
        bullets9 = [
            f"Audience: {audience}",
            f"Promise: {promise}",
            "Tone: helpful, grounded, no hype",
            "No guarantees language included",
            "Fib cadence: 1/2/3/5/8 follow-ups",
            "Φ discount: bundle ≈ 61.8% of total",
            "Keep it local-first (no cloud dependency)",
            "Add social proof when available",
            "Iterate weekly (369 cycles)",
        ]

        funnel_map = three_six_nine_sections(
            f"Lead Magnet Funnel — {topic}",
            bullets3,
            bullets6,
            bullets9,
        )

        # Lead magnet content (markdown)
        lead_md = f"""# {lead_title}

**For:** {audience}

## What you get
- A 3-step method to start
- A 6-part checklist to ship
- A 9-point clarity map to stay aligned

## 3 Steps (369)
1. Pick one outcome you can deliver this week.
2. Create one artifact that proves it.
3. Package + reuse the artifact into 2–3 more formats.

## 6-Part Shipping Checklist
1) Define a micro-result
2) Build the template
3) Add examples
4) Add FAQ + disclaimers
5) Add a simple “next step”
6) Export in a folder people can use

## 9 Prompt Starters
1) “Help me define a tiny outcome for {topic}.”
2) “Turn this outline into a 1-page checklist.”
3) “Give me 3 titles + 6 bullets + 9 hooks.”
4) “Create a short email sequence (1/2/3/5/8).”
5) “Draft a landing page with no hype.”
6) “Make a Gumroad listing with FAQs.”
7) “Suggest a Φ bundle upgrade.”
8) “Make 3 social posts + a YouTube script.”
9) “Create a weekly iteration plan (369 cycles).”

## Next step
{primary_cta}
"""

        landing_html = f"""<!doctype html>
<html><head>
<meta charset='utf-8'/><meta name='viewport' content='width=device-width, initial-scale=1'/>
<title>{lead_title}</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;max-width:900px;margin:40px auto;padding:0 16px;}}
.card{{border:1px solid #ddd;border-radius:14px;padding:18px;margin:18px 0;}}
.small{{color:#555;font-size:14px}}
button{{padding:12px 16px;border-radius:12px;border:1px solid #111;background:#111;color:#fff;font-weight:600;}}
</style>
</head><body>
<h1>{lead_title}</h1>
<p class='small'>Local-only • 369/Φ/Fib aligned • Template copy (edit freely)</p>
<div class='card'>
<h2>What you’ll get</h2>
<ul>
<li>3-step method</li>
<li>6-part shipping checklist</li>
<li>9 prompt starters</li>
</ul>
</div>
<div class='card'>
<h2>{promise}</h2>
<p><strong>For:</strong> {audience}</p>
<p><strong>CTA:</strong> {primary_cta}</p>
<button>Download (placeholder)</button>
<p class='small'>No guarantees. This is a template + guidance pack. Results depend on execution and market conditions.</p>
</div>
<div class='card'>
<h2>Upgrade</h2>
<p>Want the full system? Get <strong>{upsell_title}</strong> (includes deeper templates, bundles, and compounding assets).</p>
<button>View Upgrade (placeholder)</button>
</div>
</body></html>
"""

        email_md = """# Email Drip (Fib cadence)

**Cadence:** Day 1, 2, 3, 5, 8

## Day 1 — Quick win
- remind them of the 3 steps
- ask one question: what’s the outcome?

## Day 2 — Make it usable
- convert idea into a template
- add one example

## Day 3 — Package it
- folder structure
- naming conventions

## Day 5 — Upgrade path
- introduce the Φ bundle
- show what’s included

## Day 8 — Proof + iterate
- ask for testimonial
- share 369 iteration plan
"""

        upsell_md = f"""# Upsell Page Copy — {upsell_title}

## Offer
A complete system pack to go from idea → product constellation.

## Includes (369)
- **3** core frameworks
- **6** done-for-you templates
- **9** ready-to-sell variations (angles/tiers)

## Price positioning (Φ)
- Bundle discount target: **~61.8%** of combined individual items.

## Disclaimer
No guarantees. You’re buying a system/template pack.
"""

        funnel_map_path = os.path.join(out_dir, "FUNNEL_MAP.md")
        lead_md_path = os.path.join(out_dir, "LEAD_MAGNET.md")
        landing_path = os.path.join(out_dir, "LANDING_PAGE.html")
        email_path = os.path.join(out_dir, "EMAIL_DRIP.md")
        upsell_path = os.path.join(out_dir, "UPSELL_PAGE.md")

        write_text(funnel_map_path, funnel_map)
        write_text(lead_md_path, lead_md)
        write_text(landing_path, landing_html)
        write_text(email_path, email_md)
        write_text(upsell_path, upsell_md)

        pdf_enabled = bool(constraints.get("pdf", True))
        pdf_path = os.path.join(out_dir, "LEAD_MAGNET.pdf")
        if pdf_enabled:
            self._make_pdf(
                pdf_path,
                lead_title,
                [
                    ("3 Steps", bullets3),
                    ("6 Deliverables", bullets6),
                    ("9 Notes", bullets9),
                ],
            )

        meta = {
            "topic": topic,
            "sku": sku,
            "tier": tier,
            "price_cents": price_cents,
            "fib_days": FIB[:5],
            "audience": audience,
            "promise": promise,
        }
        meta_path = os.path.join(out_dir, "meta.json")
        write_json(meta_path, meta)

        artifacts = [funnel_map_path, lead_md_path, landing_path, email_path, upsell_path, meta_path]
        if pdf_enabled:
            artifacts.append(pdf_path)

        return ModuleResult(
            name=self.name,
            artifacts=artifacts,
            summary={"ok": True, "audience": audience, "cta": primary_cta, "pdf": pdf_enabled},
        )
