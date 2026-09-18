from __future__ import annotations
from typing import Any
from .base import ModuleResult
from .utils import ensure_dir, write_text, write_json, now_iso, slugify

class TestimonialCollector:
    """Generates a local testimonial form + templates. Submission endpoint is in the API (token-gated)."""
    name = "testimonial_collector"

    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        out_dir = f"{run_folder}/artifacts/{self.name}"
        ensure_dir(out_dir)
        form_token_hint = constraints.get("form_token_hint") or "set EV_TESTIMONIAL_FORM_TOKEN in .env"

        html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<title>Testimonial — {topic}</title>
<style>
body {{ font-family: Arial, sans-serif; max-width: 760px; margin: 30px auto; padding: 0 16px; }}
label {{ display:block; margin-top: 12px; font-weight: bold; }}
input, textarea, select {{ width: 100%; padding: 10px; margin-top: 6px; }}
small {{ color:#666; }}
button {{ margin-top: 14px; padding: 10px 14px; }}
</style>
</head>
<body>
<h1>Testimonial</h1>
<p><b>Product:</b> {sku} — {topic}</p>
<p><small>This form saves to your local app. No public posting unless you choose to share it.</small></p>

<form method="POST" action="http://127.0.0.1:18791/v1/testimonials/submit">
  <input type="hidden" name="sku" value="{sku}"/>
  <label>Form Token <small>({form_token_hint})</small></label>
  <input name="token" placeholder="token" />

  <label>Your name</label>
  <input name="name" placeholder="Jane Doe" />

  <label>Your role (optional)</label>
  <input name="role" placeholder="Wellness coach / Creator / Owner" />

  <label>Rating</label>
  <select name="rating">
    <option>5</option><option>4</option><option>3</option><option>2</option><option>1</option>
  </select>

  <label>Testimonial</label>
  <textarea name="text" rows="6" placeholder="What changed for you? What was easy? What was valuable?"></textarea>

  <label>Consent to use publicly?</label>
  <select name="consent_public">
    <option value="yes">Yes</option>
    <option value="no" selected>No</option>
  </select>

  <label>Email (optional, not shown publicly)</label>
  <input name="contact" placeholder="email@example.com" />

  <button type="submit">Submit</button>
</form>

<p><small>Tip: after you collect a few, run the module again later to generate formatted snippets for listings.</small></p>
</body>
</html>
"""

        write_text(f"{out_dir}/testimonial_form.html", html)
        write_text(f"{out_dir}/testimonials_template.csv", "sku,name,role,rating,text,consent_public,contact\n")
        readme = """# Testimonial Collector (Local)

1) Set `EV_TESTIMONIAL_FORM_TOKEN` in your `.env`
2) Run the API
3) Open `testimonial_form.html` locally in a browser
4) Submissions are stored in your local SQLite DB
5) Use `/v1/testimonials` to export to markdown snippets
"""
        write_text(f"{out_dir}/README_TESTIMONIALS.md", readme)

        write_json(f"{out_dir}/testimonial_collector.json", {"sku": sku, "topic": topic, "generated_at": now_iso()})
        return ModuleResult(name=self.name, artifacts=[f"{out_dir}/testimonial_form.html", f"{out_dir}/README_TESTIMONIALS.md", f"{out_dir}/testimonials_template.csv", f"{out_dir}/testimonial_collector.json"], summary={"ok": True})
