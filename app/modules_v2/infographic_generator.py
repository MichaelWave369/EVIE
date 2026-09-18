"""
EVIE Infographic Generator Module
Generates beautiful PNG infographics from any topic or ingested content.

Drop this file into: D:/EVIEv4.0/app/modules_v2/infographic_generator.py

Supports multiple layouts:
  - "phases"    : numbered phase cards (great for frameworks/systems)
  - "list"      : icon + title + description rows  
  - "comparison": side-by-side two-column
  - "steps"     : numbered sequential steps
  - "stats"     : big number callouts with context
  - "chakra"    : specialized 7-bar spectrum layout

Output: 1080x1920 PNG (Pinterest/Instagram portrait) or 1080x1080 square
"""

import os, json, math, re, textwrap
from pathlib import Path
from datetime import datetime
try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    Image = None
    ImageDraw = None
    ImageFont = None
from app.modules.base import BaseModule
from .base import ModuleResult


# ── Palette presets ──────────────────────────────────────────────────────────

PALETTES = {
    "porch": {
        "bg":       (45, 27, 78),
        "card":     (80, 55, 120),
        "accent":   (201, 149, 44),
        "light":    (240, 235, 248),
        "white":    (255, 255, 255),
        "muted":    (180, 160, 210),
        "text":     (255, 255, 255),
        "dark_text":(45, 27, 78),
    },
    "wellness": {
        "bg":       (30, 77, 43),
        "card":     (40, 100, 58),
        "accent":   (122, 199, 79),
        "light":    (235, 245, 235),
        "white":    (255, 255, 255),
        "muted":    (160, 210, 160),
        "text":     (255, 255, 255),
        "dark_text":(30, 77, 43),
    },
    "dark": {
        "bg":       (18, 18, 18),
        "card":     (30, 30, 30),
        "accent":   (0, 229, 255),
        "light":    (40, 40, 40),
        "white":    (255, 255, 255),
        "muted":    (140, 140, 140),
        "text":     (255, 255, 255),
        "dark_text":(18, 18, 18),
    },
    "gold": {
        "bg":       (28, 20, 10),
        "card":     (50, 35, 15),
        "accent":   (212, 175, 55),
        "light":    (255, 245, 210),
        "white":    (255, 255, 255),
        "muted":    (180, 150, 80),
        "text":     (255, 255, 255),
        "dark_text":(28, 20, 10),
    },
}


# ── Font helpers ──────────────────────────────────────────────────────────────

def _load_font(size, bold=False):
    candidates = [
        f"/usr/share/fonts/truetype/liberation/LiberationSans-{'Bold' if bold else 'Regular'}.ttf",
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'Bold' if bold else ''}.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _load_serif(size, bold=False):
    candidates = [
        f"/usr/share/fonts/truetype/liberation/LiberationSerif-{'Bold' if bold else 'Regular'}.ttf",
        f"/usr/share/fonts/truetype/freefont/FreeSerif{'Bold' if bold else ''}.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return _load_font(size, bold)


# ── Drawing helpers ───────────────────────────────────────────────────────────

def _rr(draw, xy, r, fill=None, outline=None, width=2):
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)


def _center_text(draw, text, y, font, color, W=1080, max_w=None):
    mw = max_w or W - 80
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    x = (W - tw) // 2
    draw.text((x, y), text, font=font, fill=color)


def _wrap(text, font, max_w):
    words = text.split()
    lines, cur = [], []
    for w in words:
        test = " ".join(cur + [w])
        if font.getbbox(test)[2] <= max_w:
            cur.append(w)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines


def _draw_wrapped(draw, text, x, y, font, color, max_w, line_gap=8, align="left", W=1080):
    lines = _wrap(text, font, max_w)
    cy = y
    for line in lines:
        bb = font.getbbox(line)
        lw, lh = bb[2]-bb[0], bb[3]-bb[1]
        lx = x + (max_w-lw)//2 if align == "center" else x
        draw.text((lx, cy), line, font=font, fill=color)
        cy += lh + line_gap
    return cy


def _glow(img, cx, cy, r, color, alpha=40):
    ov = Image.new("RGBA", img.size, (0,0,0,0))
    od = ImageDraw.Draw(ov)
    for i in range(4):
        a = max(5, alpha//(i+1))
        r2 = r + i*20
        od.ellipse([cx-r2, cy-r2, cx+r2, cy+r2], fill=(*color[:3], a))
    base = img.convert("RGBA")
    return Image.alpha_composite(base, ov).convert("RGB")


# ── Layout renderers ──────────────────────────────────────────────────────────

def _render_phases(draw, img, data, p, W, start_y):
    """Numbered phase cards — up to 6 items"""
    items = data.get("items", [])
    card_h = min(220, (1920 - start_y - 200) // max(len(items), 1))
    gap = 16
    margin = 50

    card_colors = [
        tuple(max(0, p["card"][i]+j*18) for i in range(3))
        for j in range(len(items))
    ]
    card_colors[-1] = p["accent"]  # Last card gold

    y = start_y
    font_num  = _load_serif(90, bold=True)
    font_name = _load_serif(34, bold=True)
    font_days = _load_font(21, bold=True)
    font_tag  = _load_font(21)
    font_desc = _load_font(23)

    for i, item in enumerate(items):
        is_accent = (i == len(items)-1)
        bg = p["accent"] if is_accent else card_colors[i]
        tc = p["dark_text"] if is_accent else p["white"]
        ac = p["dark_text"] if is_accent else p["accent"]

        _rr(draw, [margin, y, W-margin, y+card_h], 18, fill=bg,
            outline=p["accent"] if not is_accent else None, width=1)
        # Accent left bar
        _rr(draw, [margin, y, margin+7, y+card_h], 4,
            fill=p["dark_text"] if is_accent else p["accent"])

        # Big faded number
        num_str = str(i+1).zfill(2)
        draw.text((W-190, y+10), num_str, font=font_num,
                  fill=(*ac[:3], 30))

        tx = margin + 30
        draw.text((tx, y+15), item.get("name", f"Phase {i+1}"), font=font_name, fill=ac)
        draw.text((tx, y+58), item.get("days", ""), font=font_days, fill=p["muted"] if not is_accent else p["dark_text"])
        draw.text((tx, y+88), f"— {item.get('tagline','')}", font=font_tag,
                  fill=p["muted"] if not is_accent else p["dark_text"])
        draw.line([tx, y+118, W-margin-20, y+118], fill=(*p["accent"][:3], 60), width=1)
        _draw_wrapped(draw, item.get("desc",""), tx, y+130, font_desc, tc, W-margin-tx-20, line_gap=6)

        y += card_h + gap

    return y


def _render_list(draw, img, data, p, W, start_y):
    """Icon + title + body rows"""
    items = data.get("items", [])
    font_icon  = _load_font(42)
    font_title = _load_serif(30, bold=True)
    font_body  = _load_font(22)
    gap = 18
    margin = 50
    y = start_y

    for i, item in enumerate(items):
        bg = p["card"] if i % 2 == 0 else tuple(max(0,c-15) for c in p["card"])
        row_h = 130
        _rr(draw, [margin, y, W-margin, y+row_h], 14, fill=bg,
            outline=(*p["accent"][:3], 40), width=1)

        # Icon circle
        icx, icy = margin+55, y+row_h//2
        draw.ellipse([icx-36, icy-36, icx+36, icy+36], fill=tuple(max(0,c-20) for c in bg))
        draw.ellipse([icx-34, icy-34, icx+34, icy+34], outline=p["accent"], width=1)
        icon = item.get("icon","✦")
        draw.text((icx-20, icy-22), icon, font=font_icon)

        # Text
        tx = margin + 108
        draw.text((tx, y+18), item.get("title",""), font=font_title, fill=p["accent"])
        _draw_wrapped(draw, item.get("body",""), tx, y+56, font_body, p["muted"], W-margin-tx-20)

        y += row_h + gap

    return y


def _render_steps(draw, img, data, p, W, start_y):
    """Numbered sequential steps"""
    items = data.get("items", [])
    font_num   = _load_serif(42, bold=True)
    font_title = _load_serif(28, bold=True)
    font_body  = _load_font(21)
    margin = 50
    step_h = 150
    gap = 14
    y = start_y

    for i, item in enumerate(items):
        # Connector line (not last)
        if i < len(items)-1:
            draw.line([margin+40, y+step_h, margin+40, y+step_h+gap],
                     fill=(*p["accent"][:3], 60), width=3)

        _rr(draw, [margin, y, W-margin, y+step_h], 16, fill=p["card"],
            outline=(*p["accent"][:3], 50), width=1)

        # Number circle
        ncx, ncy = margin+40, y+step_h//2
        draw.ellipse([ncx-32, ncy-32, ncx+32, ncy+32], fill=p["accent"])
        bb = font_num.getbbox(str(i+1))
        nw = bb[2]-bb[0]
        draw.text((ncx-nw//2, ncy-22), str(i+1), font=font_num, fill=p["dark_text"])

        tx = margin+90
        draw.text((tx, y+22), item.get("title",""), font=font_title, fill=p["accent"])
        _draw_wrapped(draw, item.get("body",""), tx, y+60, font_body, p["text"], W-margin-tx-20)

        y += step_h + gap

    return y


def _render_stats(draw, img, data, p, W, start_y):
    """Big stat callouts in a grid"""
    items = data.get("items", [])
    cols  = 2
    margin = 50
    gap = 16
    card_w = (W - margin*2 - gap*(cols-1)) // cols
    card_h = 200
    font_stat  = _load_serif(72, bold=True)
    font_label = _load_font(22, bold=True)
    font_sub   = _load_font(19)
    y = start_y

    for i, item in enumerate(items):
        col = i % cols
        row = i // cols
        x = margin + col*(card_w+gap)
        cy = y + row*(card_h+gap)

        _rr(draw, [x, cy, x+card_w, cy+card_h], 16, fill=p["card"],
            outline=(*p["accent"][:3], 50), width=1)

        # Big stat
        stat = item.get("stat","—")
        bb = font_stat.getbbox(stat)
        sw = bb[2]-bb[0]
        sx = x + (card_w-sw)//2
        draw.text((sx, cy+18), stat, font=font_stat, fill=p["accent"])

        # Label
        label = item.get("label","")
        bb2 = font_label.getbbox(label)
        lw = bb2[2]-bb2[0]
        draw.text((x+(card_w-lw)//2, cy+98), label, font=font_label, fill=p["white"])

        # Sub
        sub = item.get("sub","")
        if sub:
            bb3 = font_sub.getbbox(sub)
            sw2 = bb3[2]-bb3[0]
            draw.text((x+(card_w-sw2)//2, cy+132), sub, font=font_sub, fill=p["muted"])

    rows = math.ceil(len(items)/cols)
    return y + rows*(card_h+gap)


def _render_comparison(draw, img, data, p, W, start_y):
    """Two-column comparison"""
    left  = data.get("left",  {})
    right = data.get("right", {})
    margin = 50
    col_w = (W - margin*2 - 20) // 2
    font_head = _load_serif(30, bold=True)
    font_item = _load_font(22)
    gap = 10

    # Headers
    _rr(draw, [margin, start_y, margin+col_w, start_y+52], 10, fill=p["accent"])
    _rr(draw, [margin+col_w+20, start_y, W-margin, start_y+52], 10, fill=p["card"])

    lh = left.get("title","")
    rh = right.get("title","")
    bb = font_head.getbbox(lh)
    draw.text((margin+(col_w-bb[2]+bb[0])//2, start_y+10), lh, font=font_head, fill=p["dark_text"])
    bb2 = font_head.getbbox(rh)
    draw.text((margin+col_w+20+(col_w-bb2[2]+bb2[0])//2, start_y+10), rh, font=font_head, fill=p["accent"])

    y = start_y + 70
    l_items = left.get("items", [])
    r_items = right.get("items", [])

    for i in range(max(len(l_items), len(r_items))):
        row_h = 70
        if i < len(l_items):
            _rr(draw, [margin, y, margin+col_w, y+row_h], 8,
                fill=tuple(max(0,c-10) for c in p["card"]))
            _draw_wrapped(draw, l_items[i], margin+12, y+10, font_item,
                         p["accent"], col_w-24)
        if i < len(r_items):
            _rr(draw, [margin+col_w+20, y, W-margin, y+row_h], 8,
                fill=tuple(max(0,c-10) for c in p["card"]))
            _draw_wrapped(draw, r_items[i], margin+col_w+32, y+10, font_item,
                         p["muted"], col_w-24)
        y += row_h + gap

    return y


# ── Main class ────────────────────────────────────────────────────────────────

class InfographicGenerator(BaseModule):
    """
    Generates beautiful PNG infographics from any topic.

    Constraint examples:
    {
        "layout": "phases",       // phases|list|steps|stats|comparison
        "theme": "porch",         // porch|wellness|dark|gold
        "size": "portrait",       // portrait (1080x1920) | square (1080x1080)
        "brand": "The Porch is Eternal",
        "url": "microneesia.gumroad.com",
        "cta": "Get the Journal — $27"
    }
    """

    name = "infographic_generator"
    description = "Generate beautiful PNG infographics for Pinterest, Instagram, or print"

    W = 1080

    def generate(
        self,
        *,
        topic: str,
        run_folder: str,
        sku: str,
        tier: str,
        price_cents: int,
        platforms: list[str],
        constraints: dict,
    ) -> ModuleResult:
        if Image is None:
            return ModuleResult(
                name=self.name,
                artifacts=[],
                summary={
                    "ok": False,
                    "error": "infographic_generator requires Pillow (PIL). Install Pillow to render PNG outputs.",
                    "missing_dependency": "Pillow",
                },
            )

        merged = dict(constraints or {})
        merged.setdefault("output_dir", run_folder)
        context = str(merged.get("context") or "")
        try:
            out = self.run(topic=topic, constraints=merged, context=context)
            artifact = out.get("artifact_path")
            artifacts = [artifact] if artifact else []
            return ModuleResult(name=self.name, artifacts=artifacts, summary=out)
        except Exception as exc:
            return ModuleResult(
                name=self.name,
                artifacts=[],
                summary={"ok": False, "error": f"infographic_generator failed: {exc}"},
            )

    def run(self, topic: str, constraints: dict, context: str = "") -> dict:
        layout    = constraints.get("layout", "phases")
        theme     = constraints.get("theme", "porch")
        size      = constraints.get("size", "portrait")
        brand     = constraints.get("brand", "The Porch is Eternal")
        url       = constraints.get("url", "microneesia.gumroad.com")
        cta       = constraints.get("cta", "")
        custom_p  = constraints.get("palette", {})

        H = 1920 if size == "portrait" else 1080
        p = {**PALETTES.get(theme, PALETTES["porch"]), **custom_p}
        W = self.W

        # Get slide data from LLM
        slide_prompt = self._build_prompt(topic, layout, context)
        raw = self._call_llm(slide_prompt)
        data = self._parse_json(raw, layout, topic)

        # Build image
        img = Image.new("RGB", (W, H), p["bg"])
        draw = ImageDraw.Draw(img)

        # Background decoration
        img = _glow(img, W//2, 200, 160, p["accent"], alpha=20)
        draw = ImageDraw.Draw(img)

        # Sacred geometry ring
        for r in [190, 165, 140]:
            draw.ellipse([W//2-r, 20, W//2+r, 20+r*2], outline=(*p["accent"][:3], 15), width=1)

        # Header section
        y = self._draw_header(draw, img, data, p, W, topic, brand)

        # Content
        if layout == "phases":
            y = _render_phases(draw, img, data, p, W, y)
        elif layout == "list":
            y = _render_list(draw, img, data, p, W, y)
        elif layout == "steps":
            y = _render_steps(draw, img, data, p, W, y)
        elif layout == "stats":
            y = _render_stats(draw, img, data, p, W, y)
        elif layout == "comparison":
            y = _render_comparison(draw, img, data, p, W, y)
        else:
            y = _render_list(draw, img, data, p, W, y)

        # Footer CTA
        self._draw_footer(draw, p, W, H, url, cta)

        # Save
        out_path = self._get_output_path(topic, constraints)
        img.save(out_path, quality=97, dpi=(300, 300))

        return {"artifact_path": out_path, "layout": layout, "theme": theme}

    def _draw_header(self, draw, img, data, p, W, topic, brand):
        font_brand    = _load_font(22, bold=True)
        font_title_lg = _load_serif(58, bold=True)
        font_subtitle = _load_font(25)

        title    = data.get("title", topic)
        subtitle = data.get("subtitle", "")

        _center_text(draw, f"✦  {brand.upper()}  ✦", 420, font_brand, p["accent"], W)
        _center_text(draw, title.upper(), 475, font_title_lg, p["white"], W)
        if subtitle:
            _center_text(draw, subtitle, 548, font_subtitle, p["muted"], W)

        draw.line([100, 600, W-100, 600], fill=p["accent"], width=2)
        draw.line([180, 608, W-180, 608], fill=(*p["muted"][:3],), width=1)

        return 630

    def _draw_footer(self, draw, p, W, H, url, cta):
        margin = 80
        box_y  = H - 160

        if cta:
            _rr(draw, [margin, box_y, W-margin, box_y+80], 18, fill=p["accent"])
            font_cta = _load_serif(30, bold=True)
            _center_text(draw, cta, box_y+22, font_cta, p["dark_text"], W)
            url_y = box_y + 95
        else:
            url_y = box_y + 20

        font_url = _load_font(22)
        _center_text(draw, url, url_y, font_url, p["muted"], W)

        font_footer = _load_font(18)
        _center_text(draw, "✦  PHI369 Labs  ✦", url_y+34, font_footer, (*p["muted"][:3],), W)

    def _build_prompt(self, topic, layout, context):
        ctx = f"\n\nDraw from this content:\n{context[:2500]}" if context else ""
        layout_instructions = {
            "phases": 'Return {"title":"...", "subtitle":"...", "items":[{"name":"...","days":"...","tagline":"...","desc":"..."},...]} with 4-6 items.',
            "list":   'Return {"title":"...", "subtitle":"...", "items":[{"icon":"emoji","title":"...","body":"..."},...]} with 5-7 items.',
            "steps":  'Return {"title":"...", "subtitle":"...", "items":[{"title":"...","body":"..."},...]} with 4-7 numbered steps.',
            "stats":  'Return {"title":"...", "subtitle":"...", "items":[{"stat":"number/symbol","label":"...","sub":"..."},...]} with 4-8 stats.',
            "comparison": 'Return {"title":"...","subtitle":"...","left":{"title":"...","items":["...",...]},"right":{"title":"...","items":["...",...]} } with 4-6 items each side.',
        }
        return f"""Create infographic content for: {topic}
Layout: {layout}
{layout_instructions.get(layout, layout_instructions["list"])}
Keep text SHORT — this is a visual infographic, not a document.
Titles: max 5 words. Bodies: max 15 words. Be punchy and clear.
Return ONLY valid JSON, no markdown fences.{ctx}"""

    def _call_llm(self, prompt):
        try:
            from app.settings import settings
            if settings.llm_backend == "anthropic":
                import anthropic
                client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
                msg = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=2000,
                    messages=[{"role":"user","content":prompt}]
                )
                return msg.content[0].text
            elif settings.llm_backend == "openai":
                from openai import OpenAI
                client = OpenAI(api_key=settings.openai_api_key)
                r = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role":"user","content":prompt}],
                    max_tokens=2000
                )
                return r.choices[0].message.content
        except Exception:
            pass
        return "{}"

    def _parse_json(self, raw, layout, topic):
        raw = re.sub(r'```json\s*|```', '', raw).strip()
        try:
            return json.loads(raw)
        except Exception:
            return {"title": topic, "subtitle": "", "items": []}

    def _get_output_path(self, topic, constraints: dict | None = None):
        slug = re.sub(r'[^a-z0-9]+', '_', topic.lower())[:40]
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        out  = Path((constraints or {}).get("output_dir") or "data/artifacts/infographics")
        out.mkdir(parents=True, exist_ok=True)
        return str(out / f"infographic_{slug}__{ts}.png")
