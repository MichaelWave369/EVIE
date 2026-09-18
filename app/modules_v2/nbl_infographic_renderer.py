"""
NotebookLM-style infographic renderer
Key design features:
  - Deep gradient background (not flat solid)
  - Glassmorphism cards (semi-transparent + glow border)
  - Dot grid subtle texture
  - Clean numbered badge system
  - Soft glow halos behind key elements  
  - Modern thin typography with wide letter-spacing on headers
  - Teal/cyan accent system on dark navy base
  - Subtle grain/noise overlay for depth
  - Clean pill tags
  - Section separators with gradient fade
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import os, math

W, H = 1080, 1920

# ── NotebookLM Palette ───────────────────────────────────────────────────────
BG_TOP      = (8,  12,  28)      # Very dark navy
BG_MID      = (12, 18,  40)      # Slightly lighter
BG_BOT      = (10, 14,  32)      # Back to dark
CARD_BG     = (18, 26,  55)      # Card surface
CARD_BORDER = (45, 80, 160)      # Card glow border
ACCENT      = (82, 196, 196)     # Teal/cyan — primary accent
ACCENT2     = (140, 100, 220)    # Soft purple — secondary
GOLD        = (201, 163, 75)     # Warm gold for brand elements
WHITE       = (255, 255, 255)
MUTED       = (140, 160, 210)    # Muted blue-white
LABEL       = (100, 140, 200)    # Dim labels
GLOW_TEAL   = (0, 200, 180)
GLOW_PURPLE = (120, 80, 200)


# ── Font loader ──────────────────────────────────────────────────────────────

def F(size, bold=False, serif=False):
    if serif:
        paths = [
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf" if bold else
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold else
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        ]
    else:
        paths = [
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-ExtraLight.ttf",
        ]
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except:
                continue
    return ImageFont.load_default()


# ── Drawing primitives ───────────────────────────────────────────────────────

def draw_gradient_bg(img):
    """Vertical gradient background with subtle radial warm center"""
    arr = np.array(img, dtype=np.float32)
    for y in range(H):
        t = y / H
        # Vertical gradient
        r = BG_TOP[0] * (1-t) + BG_BOT[0] * t
        g = BG_TOP[1] * (1-t) + BG_BOT[1] * t
        b = BG_TOP[2] * (1-t) + BG_BOT[2] * t
        arr[y, :, 0] = r
        arr[y, :, 1] = g
        arr[y, :, 2] = b

    # Subtle warm radial at center-top (gives depth)
    cx, cy_r = W//2, H//4
    for y in range(min(H, cy_r + 400)):
        for x in range(0, W, 3):
            d = math.sqrt((x-cx)**2 + (y-cy_r)**2) / 600
            warmth = max(0, 1 - d) * 8
            arr[y, x, 0] = min(255, arr[y, x, 0] + warmth)
            arr[y, x, 1] = min(255, arr[y, x, 1] + warmth * 0.3)

    return Image.fromarray(arr.astype(np.uint8))


def draw_dot_grid(img):
    """Subtle dot grid pattern — signature NotebookLM texture"""
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    spacing = 36
    dot_r = 1
    for y in range(0, H, spacing):
        for x in range(0, W, spacing):
            d.ellipse([x-dot_r, y-dot_r, x+dot_r, y+dot_r], fill=(80, 110, 180, 18))
    base = img.convert("RGBA")
    return Image.alpha_composite(base, ov).convert("RGB")


def glow_halo(img, cx, cy, r, color, alpha=35, layers=4):
    """Soft radial glow — used behind section titles and accents"""
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for i in range(layers):
        a = max(3, alpha // (i + 1))
        ri = r + i * 30
        d.ellipse([cx-ri, cy-ri, cx+ri, cy+ri], fill=(*color[:3], a))
    base = img.convert("RGBA")
    return Image.alpha_composite(base, ov).convert("RGB")


def glass_card(img, x1, y1, x2, y2, radius=20, fill_alpha=45, border_glow=True):
    """Glassmorphism card with border glow"""
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    # Card fill — semi-transparent
    d.rounded_rectangle([x1, y1, x2, y2], radius=radius,
                        fill=(*CARD_BG, fill_alpha),
                        outline=(*CARD_BORDER, 80), width=1)

    # Inner subtle lighter top edge (glass highlight)
    d.rounded_rectangle([x1+1, y1+1, x2-1, y1+60], radius=radius,
                        fill=(*WHITE, 6))

    base = img.convert("RGBA")
    result = Image.alpha_composite(base, ov).convert("RGB")

    if border_glow:
        # Soft blur on a glow layer
        glow_ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow_ov)
        gd.rounded_rectangle([x1-3, y1-3, x2+3, y2+3], radius=radius+3,
                             fill=None, outline=(*CARD_BORDER, 40), width=3)
        glow_blur = glow_ov.filter(ImageFilter.GaussianBlur(6))
        result = Image.alpha_composite(result.convert("RGBA"), glow_blur).convert("RGB")

    return result


def badge_number(draw, cx, cy, num, size=38):
    """Numbered circle badge — teal accent"""
    r = size
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=ACCENT, outline=(*ACCENT, 180), width=2)
    # Inner ring
    draw.ellipse([cx-r+3, cy-r+3, cx+r-3, cy+r-3], fill=None,
                 outline=(*WHITE, 40), width=1)
    f = F(size - 8, bold=True)
    txt = str(num)
    bb = f.getbbox(txt)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]
    draw.text((cx - tw//2, cy - th//2 - 2), txt, font=f, fill=(8, 20, 40))


def pill_tag(draw, x, y, text, color=ACCENT):
    """Small pill/badge tag"""
    f = F(19, bold=True)
    bb = f.getbbox(text)
    tw = bb[2] - bb[0]
    pad_x, pad_y = 16, 6
    w = tw + pad_x * 2
    h = 32
    draw.rounded_rectangle([x, y, x+w, y+h], radius=16,
                           fill=(*color[:3], 30), outline=(*color[:3], 90), width=1)
    draw.text((x + pad_x, y + pad_y - 1), text, font=f, fill=color)
    return x + w + 10


def cx_text(draw, text, y, font, color, max_w=W-100):
    """Center-aligned text"""
    bb = font.getbbox(text)
    tw = bb[2] - bb[0]
    x = (W - tw) // 2
    draw.text((x, y), text, font=font, fill=color)


def wrap_draw(draw, text, x, y, font, color, max_w, gap=7, align="left"):
    """Wrap and draw text, return final y"""
    words = text.split()
    lines, cur = [], []
    for w in words:
        t = " ".join(cur + [w])
        if font.getbbox(t)[2] <= max_w:
            cur.append(w)
        else:
            if cur: lines.append(" ".join(cur))
            cur = [w]
    if cur: lines.append(" ".join(cur))

    cy = y
    for line in lines:
        bb = font.getbbox(line)
        lw = bb[2]-bb[0]
        lh = bb[3]-bb[1]
        lx = x + (max_w - lw)//2 if align == "center" else x
        draw.text((lx, cy), line, font=font, fill=color)
        cy += lh + gap
    return cy


def gradient_line(img, y, alpha=60):
    """Horizontal gradient separator line — fades at edges"""
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for x in range(W):
        t = x / W
        # Fade in from left, fade out at right
        fade = math.sin(t * math.pi)
        a = int(alpha * fade)
        d.point((x, y), fill=(*ACCENT[:3], a))
    base = img.convert("RGBA")
    return Image.alpha_composite(base, ov).convert("RGB")


def add_noise(img, intensity=6):
    """Subtle film grain — prevents flat digital look"""
    arr = np.array(img, dtype=np.int16)
    noise = np.random.randint(-intensity, intensity, arr.shape, dtype=np.int16)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


# ════════════════════════════════════════════════════════════════════════════
# BUILD THE INFOGRAPHIC
# ════════════════════════════════════════════════════════════════════════════

# --- Base ---
img = Image.new("RGB", (W, H), BG_TOP)
img = draw_gradient_bg(img)
img = draw_dot_grid(img)

# --- Top glow halos ---
img = glow_halo(img, W//2, 180, 200, GLOW_TEAL, alpha=28, layers=5)
img = glow_halo(img, W//2 - 200, 180, 120, GLOW_PURPLE, alpha=15, layers=3)
draw = ImageDraw.Draw(img)

# ── HEADER ───────────────────────────────────────────────────────────────────

# Brand label
f_brand = F(21, bold=True)
brand_txt = "✦   T H E   P O R C H   I S   E T E R N A L   ✦"
bb = f_brand.getbbox(brand_txt)
bw = bb[2]-bb[0]
draw.text(((W-bw)//2, 52), brand_txt, font=f_brand, fill=GOLD)

# Subtitle pill tags row
py = 95
px = pill_tag(draw, 0, py, "Crystal Practices", ACCENT)
px = pill_tag(draw, px, py, "Chakra Alignment", ACCENT2)
px = pill_tag(draw, px, py, "Gene Keys", GOLD)
px = pill_tag(draw, px, py, "Rhythm Code", ACCENT)
# center them
total_w = px - 10
start_x = (W - total_w) // 2
# Redraw centered
img_pil = img.copy()
draw2 = ImageDraw.Draw(img_pil)
py = 95
px2 = start_x
px2 = pill_tag(draw2, px2, py, "Crystal Practices", ACCENT)
px2 = pill_tag(draw2, px2, py, "Chakra Alignment", ACCENT2)
px2 = pill_tag(draw2, px2, py, "Gene Keys", GOLD)
px2 = pill_tag(draw2, px2, py, "Rhythm Code", ACCENT)
img = img_pil
draw = ImageDraw.Draw(img)

# Main title
f_title = F(70, bold=True, serif=True)
f_title2 = F(58, bold=True, serif=True)
cx_text(draw, "30-Day Sovereign", 145, f_title, WHITE)
cx_text(draw, "Body Transformation", 222, f_title2, ACCENT)

# Tagline
f_tag = F(24)
cx_text(draw, "A complete re-patterning of how you relate to your body.", 305, f_tag, MUTED)

# Gradient separator
img = gradient_line(img, 345, alpha=70)
img = gradient_line(img, 347, alpha=35)
draw = ImageDraw.Draw(img)

# ── SECTION LABEL ────────────────────────────────────────────────────────────
f_section = F(18, bold=True)
draw.text((60, 368), "THE FRAMEWORK", font=f_section, fill=LABEL)
# Accent dot
draw.ellipse([200, 376, 207, 383], fill=ACCENT)

# ── PHASE CARDS ─────────────────────────────────────────────────────────────
PHASES = [
    {
        "num": 1, "name": "SEED",
        "days": "Days 1 – 9",
        "tag": "Identity Map",
        "color": ACCENT,
        "desc": "Who are you becoming? Plant the energetic foundation. Name yourself into your next chapter with daily crystal and journal work.",
    },
    {
        "num": 2, "name": "BUILD",
        "days": "Days 10 – 18",
        "tag": "Cycle Intelligence",
        "color": (100, 160, 255),
        "desc": "Remove friction. Install rhythm. Align with solar, lunar, and nervous system cycles. Design your morning and evening bookends.",
    },
    {
        "num": 3, "name": "REVEAL",
        "days": "Days 19 – 27",
        "tag": "Sacred Refinement",
        "color": ACCENT2,
        "desc": "Shadow work. Gene Keys contemplation. Christos Oil integrity practice. Ancestral wound and gift transformation.",
    },
    {
        "num": 4, "name": "SEAL",
        "days": "Days 28 – 30",
        "tag": "Lock It In",
        "color": GOLD,
        "desc": "Ceremony. Sovereign vow. Your personal Rhythm Code dashboard signed and sealed for life.",
    },
]

card_margin = 50
card_gap = 16
card_h = 200
card_y = 400

for i, ph in enumerate(PHASES):
    y1 = card_y + i * (card_h + card_gap)
    y2 = y1 + card_h
    x1, x2 = card_margin, W - card_margin
    color = ph["color"]

    img = glass_card(img, x1, y1, x2, y2, radius=18, fill_alpha=50)
    draw = ImageDraw.Draw(img)

    # Left color bar
    draw.rounded_rectangle([x1, y1, x1+5, y2], radius=3, fill=color)

    # Badge
    badge_number(draw, x1 + 50, y1 + card_h//2, ph["num"], size=30)

    # Phase name
    f_name = F(38, bold=True, serif=True)
    draw.text((x1 + 100, y1 + 22), ph["name"], font=f_name, fill=color)

    # Tag pill inline
    pill_tag(draw, x1 + 100, y1 + 70, ph["tag"], color)

    # Days
    f_days = F(20, bold=True)
    draw.text((x1 + 100, y1 + 112), ph["days"], font=f_days, fill=MUTED)

    # Desc
    f_desc = F(21)
    wrap_draw(draw, ph["desc"], x1 + 100, y1 + 138, f_desc, (*MUTED[:3],), x2 - x1 - 115, gap=5)

    # Faded phase number watermark top-right
    f_wm = F(90, bold=True, serif=True)
    wm = str(ph["num"]).zfill(2)
    bb = f_wm.getbbox(wm)
    ww = bb[2]-bb[0]
    ov2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d2 = ImageDraw.Draw(ov2)
    d2.text((x2 - ww - 25, y1 + 10), wm, font=f_wm, fill=(*color[:3], 20))
    img = Image.alpha_composite(img.convert("RGBA"), ov2).convert("RGB")
    draw = ImageDraw.Draw(img)

# ── SECTION: DAILY PRACTICE ──────────────────────────────────────────────────
section2_y = card_y + 4*(card_h + card_gap) + 20

img = gradient_line(img, section2_y, alpha=55)
draw = ImageDraw.Draw(img)

img = glow_halo(img, W//2, section2_y + 80, 160, GLOW_TEAL, alpha=18, layers=3)
draw = ImageDraw.Draw(img)

draw.text((60, section2_y + 18), "DAILY PRACTICE SYSTEM", font=f_section, fill=LABEL)
draw.ellipse([280, section2_y+26, 287, section2_y+33], fill=ACCENT)

PRACTICES = [
    ("🔮", "Crystal", "Stone pairing\n+ intention"),
    ("✦",  "Chakra",  "Targeted\naffirmation"),
    ("🌀", "Coherence", "Spoken\nvow"),
    ("📖", "Journal",  "4-5 deep\nprompts"),
    ("🎵", "Sound",    "Solfeggio\nfrequency"),
]

prac_y = section2_y + 55
prac_w = (W - 80) // len(PRACTICES)

for i, (icon, name, sub) in enumerate(PRACTICES):
    px3 = 40 + i * prac_w
    cx3 = px3 + prac_w//2

    # Circle card
    img = glass_card(img, cx3 - 50, prac_y, cx3 + 50, prac_y + 150, radius=16, fill_alpha=40)
    draw = ImageDraw.Draw(img)

    # Glow ring
    draw.ellipse([cx3-42, prac_y+12, cx3+42, prac_y+96], outline=(*ACCENT[:3], 40), width=1)

    # Icon
    f_icon = F(38)
    ib = f_icon.getbbox(icon)
    iw = ib[2]-ib[0]
    draw.text((cx3 - iw//2, prac_y + 22), icon, font=f_icon)

    # Name
    f_pn = F(19, bold=True)
    nb = f_pn.getbbox(name)
    nw = nb[2]-nb[0]
    draw.text((cx3 - nw//2, prac_y + 98), name, font=f_pn, fill=ACCENT)

    # Sub
    f_sub2 = F(16)
    for j, sl in enumerate(sub.split('\n')):
        sb = f_sub2.getbbox(sl)
        sw2 = sb[2]-sb[0]
        draw.text((cx3 - sw2//2, prac_y + 122 + j*18), sl, font=f_sub2, fill=MUTED)

# ── SECTION: CHAKRA BAR ──────────────────────────────────────────────────────
chakra_y = prac_y + 185

img = gradient_line(img, chakra_y - 10, alpha=40)
draw = ImageDraw.Draw(img)
draw.text((60, chakra_y + 5), "7-CHAKRA ALIGNMENT", font=f_section, fill=LABEL)

CHAKRAS = [
    ((155, 89, 182), "Crown"),
    ((74,  35,  90), "3rd Eye"),
    ((26,  82, 118), "Throat"),
    ((30, 132,  73), "Heart"),
    ((183,149,  11), "Solar"),
    ((186, 74,   0), "Sacral"),
    ((146, 43,  33), "Root"),
]

bar_y = chakra_y + 38
bar_h2 = 44
bar_w2 = (W - 100) // len(CHAKRAS) - 4
f_cl = F(16, bold=True)

for i, (col, nm) in enumerate(CHAKRAS):
    bx = 50 + i * (bar_w2 + 4)
    # Glowing bar
    img_ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dov = ImageDraw.Draw(img_ov)
    dov.rounded_rectangle([bx-2, bar_y-2, bx+bar_w2+2, bar_y+bar_h2+2],
                          radius=8, fill=(*col, 35))
    dov.rounded_rectangle([bx, bar_y, bx+bar_w2, bar_y+bar_h2],
                          radius=6, fill=(*col, 160))
    img = Image.alpha_composite(img.convert("RGBA"), img_ov).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Label
    bb4 = f_cl.getbbox(nm)
    lw4 = bb4[2]-bb4[0]
    draw.text((bx + (bar_w2-lw4)//2, bar_y + bar_h2 + 7), nm, font=f_cl, fill=MUTED)

# ── SECTION: CRYSTALS ────────────────────────────────────────────────────────
cry_y = bar_y + bar_h2 + 65

img = gradient_line(img, cry_y - 15, alpha=40)
draw = ImageDraw.Draw(img)
draw.text((60, cry_y - 2), "KEY CRYSTAL PAIRINGS", font=f_section, fill=LABEL)

CRYSTALS = [
    ("Clear\nQuartz", ACCENT,            "Amplify"),
    ("Citrine",       (220, 180, 50),    "Abundance"),
    ("Rose\nQuartz",  (220, 140, 160),   "Heart"),
    ("Amethyst",      (140, 100, 200),   "Intuition"),
    ("Selenite",      (200, 210, 230),   "Ceremony"),
]

ccard_w = (W - 80) // len(CRYSTALS) - 6
cry_card_y = cry_y + 35

for i, (nm, col, prop) in enumerate(CRYSTALS):
    cx4 = 40 + i*(ccard_w+6) + ccard_w//2
    img = glass_card(img, cx4-ccard_w//2, cry_card_y, cx4+ccard_w//2, cry_card_y+130, radius=14, fill_alpha=35)
    draw = ImageDraw.Draw(img)

    # Crystal diamond shape
    ds = 28
    pts = [(cx4, cry_card_y+16), (cx4+ds, cry_card_y+16+ds),
           (cx4, cry_card_y+16+ds*2), (cx4-ds, cry_card_y+16+ds)]
    draw.polygon(pts, fill=(*col[:3], 160), outline=(*col[:3], 220))
    # Inner
    ds2 = 18
    pts2 = [(cx4, cry_card_y+22), (cx4+ds2, cry_card_y+22+ds2),
            (cx4, cry_card_y+22+ds2*2), (cx4-ds2, cry_card_y+22+ds2)]
    draw.polygon(pts2, fill=(*col[:3], 80))

    f_cn = F(18, bold=True)
    f_cp = F(16)
    for j, ln in enumerate(nm.split('\n')):
        bb5 = f_cn.getbbox(ln)
        lw5 = bb5[2]-bb5[0]
        draw.text((cx4-lw5//2, cry_card_y+80+j*20), ln, font=f_cn, fill=WHITE)

    bb6 = f_cp.getbbox(prop)
    pw = bb6[2]-bb6[0]
    draw.text((cx4-pw//2, cry_card_y+110), prop, font=f_cp, fill=col)

# ── CTA SECTION ──────────────────────────────────────────────────────────────
cta_y = cry_card_y + 165

img = glow_halo(img, W//2, cta_y + 60, 180, GLOW_TEAL, alpha=22, layers=4)
draw = ImageDraw.Draw(img)
img = gradient_line(img, cta_y - 15, alpha=55)
draw = ImageDraw.Draw(img)

# CTA card
img = glass_card(img, 60, cta_y, W-60, cta_y+140, radius=20, fill_alpha=60)
draw = ImageDraw.Draw(img)

# Accent top line on CTA card
draw.rounded_rectangle([60, cta_y, W-60, cta_y+3], radius=2, fill=ACCENT)

f_cta = F(36, bold=True, serif=True)
cx_text(draw, "Get the Journal — $27", cta_y + 28, f_cta, WHITE)

f_url = F(24)
cx_text(draw, "microneesia.gumroad.com", cta_y + 82, f_url, ACCENT)

f_foot = F(18)
cx_text(draw, "✦  The Porch is Eternal  ·  PHI369 Labs  ✦", cta_y + 115, f_foot, MUTED)

# ── FINAL POLISH ─────────────────────────────────────────────────────────────
# Subtle noise grain for depth
img = add_noise(img, intensity=4)

# Very slight vignette edges
ov_v = Image.new("RGBA", (W, H), (0, 0, 0, 0))
for edge_w in range(80):
    alpha_v = int((80 - edge_w) / 80 * 60)
    ov_v_d = ImageDraw.Draw(ov_v)
    ov_v_d.rectangle([edge_w, 0, edge_w, H], fill=(0, 0, 0, alpha_v))
    ov_v_d.rectangle([W-edge_w, 0, W-edge_w, H], fill=(0, 0, 0, alpha_v))
img = Image.alpha_composite(img.convert("RGBA"), ov_v).convert("RGB")

out = "/mnt/user-data/outputs/SovereignBody_NBL_Infographic.png"
img.save(out, quality=97, dpi=(300, 300))
print(f"DONE: {out}")
