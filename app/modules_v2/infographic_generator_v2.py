"""
EVIE Infographic Generator v2 — AI-Powered
Upgrades the NotebookLM-style renderer to use:
  1. ComfyUI/FLUX background (photorealistic AI generated)
  2. PIL glass card overlay compositing on top
  3. VectorFX SVG elements auto-detected and composited
  4. VisionFX final enhancement pass (optional)

Drop into: D:/EVIEv4.0/app/modules_v2/infographic_generator_v2.py
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np
import os, re, math
from pathlib import Path
from datetime import datetime
from typing import Optional

# Import connectors (adjust path if needed ***after installing***)
# from .comfyui_connector import generate_background, build_prompt_for_topic, is_comfyui_running
# from .fx_handoff import send_to_visionfx, get_all_vectorfx_outputs, composite_svg_on_image

W, H = 1080, 1920

# NBL Palette
BG_TOP      = (8,  12,  28)
CARD_BG     = (18, 26,  55)
CARD_BORDER = (45, 80, 160)
ACCENT      = (82, 196, 196)
ACCENT2     = (140, 100, 220)
GOLD        = (201, 163, 75)
WHITE       = (255, 255, 255)
MUTED       = (140, 160, 210)
LABEL       = (100, 140, 200)
GLOW_TEAL   = (0, 200, 180)


def F(size, bold=False, serif=False):
    paths = []
    if serif:
        paths = [
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        ]
    else:
        paths = [
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    for p in paths:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: continue
    return ImageFont.load_default()


def blend_ai_background(ai_bg_path: str, size: tuple = (W, H)) -> Image.Image:
    """
    Load AI-generated background, resize to target, apply cinematic color grade.
    Darkens it so text remains readable. Applies teal/purple color shift.
    """
    bg = Image.open(ai_bg_path).convert("RGB")
    
    # Resize/crop to target size
    bw, bh = bg.size
    scale = max(size[0]/bw, size[1]/bh)
    new_size = (int(bw*scale), int(bh*scale))
    bg = bg.resize(new_size, Image.LANCZOS)
    
    # Center crop
    x = (bg.width - size[0]) // 2
    y = (bg.height - size[1]) // 2
    bg = bg.crop((x, y, x+size[0], y+size[1]))
    
    # Darken for text readability (multiply by 0.45)
    arr = np.array(bg, dtype=np.float32)
    arr *= 0.45
    
    # Subtle teal color push (shift toward brand palette)
    arr[:, :, 0] *= 0.85   # reduce red
    arr[:, :, 2] *= 1.12   # boost blue slightly
    
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def draw_gradient_overlay(img: Image.Image) -> Image.Image:
    """Apply gradient overlays — darkens top+bottom, keeps center readable."""
    arr = np.array(img, dtype=np.float32)
    for y in range(H):
        t = y / H
        # Dark at top (stronger), lighter in middle, dark at bottom
        top_fade = max(0, 1 - t * 3) * 0.4
        bot_fade = max(0, (t - 0.7) / 0.3) * 0.5
        fade = top_fade + bot_fade
        arr[y] *= (1 - fade)
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8))


def add_dot_grid(img: Image.Image, alpha: int = 18) -> Image.Image:
    ov = Image.new("RGBA", (W, H), (0,0,0,0))
    d = ImageDraw.Draw(ov)
    for y in range(0, H, 36):
        for x in range(0, W, 36):
            d.ellipse([x-1,y-1,x+1,y+1], fill=(80,110,180,alpha))
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


def glow_halo(img, cx, cy, r, color, alpha=30, layers=5):
    ov = Image.new("RGBA", (W,H), (0,0,0,0))
    d = ImageDraw.Draw(ov)
    for i in range(layers):
        a = max(3, alpha//(i+1))
        ri = r + i*32
        d.ellipse([cx-ri,cy-ri,cx+ri,cy+ri], fill=(*color[:3],a))
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


def glass_card(img, x1, y1, x2, y2, radius=20, alpha=55, glow=True):
    ov = Image.new("RGBA", (W,H), (0,0,0,0))
    d = ImageDraw.Draw(ov)
    d.rounded_rectangle([x1,y1,x2,y2], radius=radius,
                        fill=(*CARD_BG, alpha),
                        outline=(*CARD_BORDER,75), width=1)
    # Glass highlight
    d.rounded_rectangle([x1+1,y1+1,x2-1,y1+55], radius=radius,
                        fill=(*WHITE,5))
    result = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    if glow:
        glow_ov = Image.new("RGBA", (W,H), (0,0,0,0))
        gd = ImageDraw.Draw(glow_ov)
        gd.rounded_rectangle([x1-3,y1-3,x2+3,y2+3], radius=radius+3,
                             fill=None, outline=(*CARD_BORDER,35), width=3)
        glow_blur = glow_ov.filter(ImageFilter.GaussianBlur(7))
        result = Image.alpha_composite(result.convert("RGBA"), glow_blur).convert("RGB")
    return result


def badge_num(draw, cx, cy, num, size=32):
    r = size
    draw.ellipse([cx-r,cy-r,cx+r,cy+r], fill=ACCENT)
    draw.ellipse([cx-r+3,cy-r+3,cx+r-3,cy+r-3], fill=None, outline=(*WHITE,40), width=1)
    f = F(size-8, bold=True)
    t = str(num)
    bb = f.getbbox(t)
    tw,th = bb[2]-bb[0], bb[3]-bb[1]
    draw.text((cx-tw//2, cy-th//2-2), t, font=f, fill=(8,20,40))


def pill_tag(draw, x, y, text, color=ACCENT):
    f = F(19, bold=True)
    bb = f.getbbox(text)
    tw = bb[2]-bb[0]
    pad = 16
    w = tw + pad*2
    draw.rounded_rectangle([x,y,x+w,y+30], radius=15,
                           fill=(*color[:3],28), outline=(*color[:3],85), width=1)
    draw.text((x+pad, y+5), text, font=f, fill=color)
    return x+w+10


def cx_text(draw, text, y, font, color):
    bb = font.getbbox(text)
    tw = bb[2]-bb[0]
    draw.text(((W-tw)//2, y), text, font=font, fill=color)


def wrap_draw(draw, text, x, y, font, color, max_w, gap=6):
    words = text.split()
    lines, cur = [], []
    for w in words:
        t = " ".join(cur+[w])
        if font.getbbox(t)[2] <= max_w:
            cur.append(w)
        else:
            if cur: lines.append(" ".join(cur))
            cur = [w]
    if cur: lines.append(" ".join(cur))
    cy = y
    for line in lines:
        bb = font.getbbox(line)
        draw.text((x,cy), line, font=font, fill=color)
        cy += bb[3]-bb[1]+gap
    return cy


def add_noise(img, intensity=5):
    arr = np.array(img, dtype=np.int16)
    noise = np.random.randint(-intensity, intensity, arr.shape, dtype=np.int16)
    return Image.fromarray(np.clip(arr+noise, 0, 255).astype(np.uint8))


def add_vignette(img, strength=55):
    ov = Image.new("RGBA", (W,H), (0,0,0,0))
    for e in range(80):
        a = int((80-e)/80 * strength)
        ov_d = ImageDraw.Draw(ov)
        ov_d.rectangle([e,0,e,H], fill=(0,0,0,a))
        ov_d.rectangle([W-e,0,W-e,H], fill=(0,0,0,a))
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


# ── Main render function ──────────────────────────────────────────────────────

def render_infographic(
    title: str,
    subtitle: str,
    phases: list,        # [{num, name, days, tag, color, desc}, ...]
    practices: list,     # [{icon, name, desc}, ...]
    crystals: list,      # [{name, color, property}, ...]
    chakras: list,       # [(color_tuple, name), ...]
    cta_text: str,
    cta_url: str,
    brand: str,
    ai_background_path: Optional[str] = None,   # Path to ComfyUI-generated PNG
    vectorfx_svg_path: Optional[str] = None,     # Path to VectorFX SVG overlay
    tags: list = None,
) -> Image.Image:
    """
    Full infographic renderer with optional AI background and SVG overlay.
    Falls back to programmatic gradient if no AI background provided.
    """

    # ── STEP 1: Background ────────────────────────────────────────────────
    if ai_background_path and Path(ai_background_path).exists():
        print("  🖼️  Using AI-generated background from ComfyUI")
        img = blend_ai_background(ai_background_path, (W, H))
        img = draw_gradient_overlay(img)
    else:
        print("  🎨  Using programmatic gradient background")
        arr = np.full((H, W, 3), BG_TOP, dtype=np.uint8)
        for y in range(H):
            t = y/H
            warm = (1-t)*10
            arr[y,:,0] = np.clip(BG_TOP[0]+warm, 0, 255)
        img = Image.fromarray(arr)

    img = add_dot_grid(img, alpha=20)

    # ── STEP 2: Glow halos ────────────────────────────────────────────────
    img = glow_halo(img, W//2, 200, 200, GLOW_TEAL, alpha=25, layers=5)
    img = glow_halo(img, W//4, 200, 120, (120,80,200), alpha=15, layers=3)

    draw = ImageDraw.Draw(img)

    # ── STEP 3: Brand header ──────────────────────────────────────────────
    f_brand = F(21, bold=True)
    bt = f"✦   {brand.upper()}   ✦"
    bb = f_brand.getbbox(bt)
    draw.text(((W-(bb[2]-bb[0]))//2, 50), bt, font=f_brand, fill=GOLD)

    # Tags
    if tags:
        tag_total = sum(F(19,bold=True).getbbox(t)[2]-F(19,bold=True).getbbox(t)[0]+42 for t in tags) + len(tags)*10
        tx = (W - tag_total)//2
        for tag_text in tags:
            tx = pill_tag(draw, tx, 92, tag_text, ACCENT if tags.index(tag_text)%2==0 else ACCENT2)

    # Main title
    f_t1 = F(68, bold=True, serif=True)
    f_t2 = F(56, bold=True, serif=True)
    cx_text(draw, title.split()[0] if len(title.split()) > 1 else title, 145, f_t1, WHITE)
    if len(title.split()) > 1:
        cx_text(draw, " ".join(title.split()[1:]), 224, f_t1, ACCENT)

    # Subtitle
    f_sub_main = F(22)
    cx_text(draw, subtitle, 315, f_sub_main, MUTED)

    # Separator
    for i, y_sep in enumerate([348, 350]):
        lw = int(W*0.7)
        ov_sep = Image.new("RGBA", (W,H), (0,0,0,0))
        sep_d = ImageDraw.Draw(ov_sep)
        for x in range(W):
            fade = math.sin(x/W * math.pi)
            a = int((70 if i==0 else 35) * fade)
            sep_d.point((x, y_sep), fill=(*ACCENT, a))
        img = Image.alpha_composite(img.convert("RGBA"), ov_sep).convert("RGB")
        draw = ImageDraw.Draw(img)

    # ── STEP 4: Phase cards ────────────────────────────────────────────────
    f_section = F(18, bold=True)
    draw.text((60, 368), "THE FRAMEWORK", font=f_section, fill=LABEL)
    draw.ellipse([202,376,209,383], fill=ACCENT)

    card_h = 195
    card_gap = 15
    card_y = 400
    CARD_X1, CARD_X2 = 50, W-50

    for i, ph in enumerate(phases):
        y1 = card_y + i*(card_h+card_gap)
        y2 = y1+card_h
        color = ph.get("color", ACCENT)
        if isinstance(color, str):
            color = tuple(int(color[j:j+2],16) for j in (0,2,4))

        img = glass_card(img, CARD_X1, y1, CARD_X2, y2, radius=18, alpha=52)
        draw = ImageDraw.Draw(img)

        # Color bar left
        draw.rounded_rectangle([CARD_X1, y1, CARD_X1+5, y2], radius=3, fill=color)

        # Badge
        badge_num(draw, CARD_X1+50, y1+card_h//2, ph["num"], size=28)

        # Name
        f_name = F(36, bold=True, serif=True)
        draw.text((CARD_X1+98, y1+20), ph["name"], font=f_name, fill=color)

        # Tag
        pill_tag(draw, CARD_X1+98, y1+66, ph.get("tag",""), color)

        # Days
        f_days = F(19, bold=True)
        draw.text((CARD_X1+98, y1+106), ph.get("days",""), font=f_days, fill=MUTED)

        # Desc
        f_desc = F(20)
        wrap_draw(draw, ph.get("desc",""), CARD_X1+98, y1+132,
                 f_desc, MUTED, CARD_X2-CARD_X1-110, gap=5)

        # Watermark number
        f_wm = F(88, bold=True, serif=True)
        wm = str(ph["num"]).zfill(2)
        wm_ov = Image.new("RGBA", (W,H), (0,0,0,0))
        wm_d = ImageDraw.Draw(wm_ov)
        wm_bb = f_wm.getbbox(wm)
        wm_d.text((CARD_X2-(wm_bb[2]-wm_bb[0])-22, y1+8), wm, font=f_wm, fill=(*color[:3],18))
        img = Image.alpha_composite(img.convert("RGBA"), wm_ov).convert("RGB")
        draw = ImageDraw.Draw(img)

    # ── STEP 5: Daily practice ─────────────────────────────────────────────
    prac_section_y = card_y + len(phases)*(card_h+card_gap) + 20
    img = glow_halo(img, W//2, prac_section_y+80, 150, GLOW_TEAL, alpha=18, layers=3)
    draw = ImageDraw.Draw(img)

    # Separator
    sep_ov = Image.new("RGBA", (W,H), (0,0,0,0))
    sep_d2 = ImageDraw.Draw(sep_ov)
    for x in range(W):
        a = int(55 * math.sin(x/W*math.pi))
        sep_d2.point((x, prac_section_y), fill=(*ACCENT, a))
    img = Image.alpha_composite(img.convert("RGBA"), sep_ov).convert("RGB")
    draw = ImageDraw.Draw(img)

    draw.text((60, prac_section_y+16), "DAILY PRACTICE SYSTEM", font=f_section, fill=LABEL)

    prac_y = prac_section_y + 55
    prac_w = (W-80) // len(practices) - 4

    for i, prac in enumerate(practices):
        px = 40 + i*(prac_w+6)
        cx_p = px + prac_w//2
        color_p = prac.get("color", ACCENT)
        if isinstance(color_p, str):
            color_p = ACCENT

        img = glass_card(img, cx_p-prac_w//2, prac_y, cx_p+prac_w//2, prac_y+148, radius=16, alpha=42)
        draw = ImageDraw.Draw(img)

        draw.ellipse([cx_p-40,prac_y+10,cx_p+40,prac_y+90], outline=(*ACCENT,38), width=1)

        f_icon = F(36)
        ib = f_icon.getbbox(prac["icon"])
        iw = ib[2]-ib[0]
        draw.text((cx_p-iw//2, prac_y+20), prac["icon"], font=f_icon)

        f_pn = F(18, bold=True)
        nb = f_pn.getbbox(prac["name"])
        nw = nb[2]-nb[0]
        draw.text((cx_p-nw//2, prac_y+96), prac["name"], font=f_pn, fill=ACCENT)

        f_sub = F(15)
        for j, sl in enumerate(prac.get("sub","").split('\n')):
            sb = f_sub.getbbox(sl)
            sw2 = sb[2]-sb[0]
            draw.text((cx_p-sw2//2, prac_y+120+j*17), sl, font=f_sub, fill=MUTED)

    # ── STEP 6: Chakra bar ─────────────────────────────────────────────────
    chakra_y = prac_y + 182
    sep_ov3 = Image.new("RGBA", (W,H), (0,0,0,0))
    sep_d3 = ImageDraw.Draw(sep_ov3)
    for x in range(W):
        a = int(40 * math.sin(x/W*math.pi))
        sep_d3.point((x, chakra_y-10), fill=(*ACCENT, a))
    img = Image.alpha_composite(img.convert("RGBA"), sep_ov3).convert("RGB")
    draw = ImageDraw.Draw(img)

    draw.text((60, chakra_y+4), "7-CHAKRA ALIGNMENT", font=f_section, fill=LABEL)

    bar_y2 = chakra_y+38
    bar_h2 = 44
    bar_w2 = (W-100)//len(chakras) - 3
    f_cl = F(15, bold=True)

    for i, (col, nm) in enumerate(chakras):
        bx = 50 + i*(bar_w2+3)
        bar_ov = Image.new("RGBA", (W,H), (0,0,0,0))
        bov_d = ImageDraw.Draw(bar_ov)
        bov_d.rounded_rectangle([bx-2,bar_y2-2,bx+bar_w2+2,bar_y2+bar_h2+2],
                               radius=8, fill=(*col,30))
        bov_d.rounded_rectangle([bx,bar_y2,bx+bar_w2,bar_y2+bar_h2],
                               radius=6, fill=(*col,155))
        img = Image.alpha_composite(img.convert("RGBA"), bar_ov).convert("RGB")
        draw = ImageDraw.Draw(img)
        bb4 = f_cl.getbbox(nm)
        lw4 = bb4[2]-bb4[0]
        draw.text((bx+(bar_w2-lw4)//2, bar_y2+bar_h2+7), nm, font=f_cl, fill=MUTED)

    # ── STEP 7: Crystals ───────────────────────────────────────────────────
    cry_y = bar_y2 + bar_h2 + 62
    sep_ov4 = Image.new("RGBA", (W,H), (0,0,0,0))
    sep_d4 = ImageDraw.Draw(sep_ov4)
    for x in range(W):
        a = int(40 * math.sin(x/W*math.pi))
        sep_d4.point((x, cry_y-15), fill=(*ACCENT, a))
    img = Image.alpha_composite(img.convert("RGBA"), sep_ov4).convert("RGB")
    draw = ImageDraw.Draw(img)

    draw.text((60, cry_y), "KEY CRYSTAL PAIRINGS", font=f_section, fill=LABEL)

    ccard_w = (W-80)//len(crystals) - 5
    cry_card_y = cry_y+34

    for i, crys in enumerate(crystals):
        cx4 = 40 + i*(ccard_w+5) + ccard_w//2
        col = crys.get("color", ACCENT)
        if isinstance(col, str):
            col = ACCENT

        img = glass_card(img, cx4-ccard_w//2, cry_card_y, cx4+ccard_w//2, cry_card_y+128, radius=14, alpha=35)
        draw = ImageDraw.Draw(img)

        # Diamond icon
        ds = 26
        pts = [(cx4,cry_card_y+14),(cx4+ds,cry_card_y+14+ds),(cx4,cry_card_y+14+ds*2),(cx4-ds,cry_card_y+14+ds)]
        draw.polygon(pts, fill=(*col[:3],155), outline=(*col[:3],215))
        ds2=17
        pts2 = [(cx4,cry_card_y+20),(cx4+ds2,cry_card_y+20+ds2),(cx4,cry_card_y+20+ds2*2),(cx4-ds2,cry_card_y+20+ds2)]
        draw.polygon(pts2, fill=(*col[:3],75))

        f_cn = F(17, bold=True)
        for j, ln in enumerate(crys["name"].split('\n')):
            bb5 = f_cn.getbbox(ln)
            draw.text((cx4-(bb5[2]-bb5[0])//2, cry_card_y+78+j*19), ln, font=f_cn, fill=WHITE)

        f_prop = F(15)
        bb6 = f_prop.getbbox(crys.get("property",""))
        draw.text((cx4-(bb6[2]-bb6[0])//2, cry_card_y+107), crys.get("property",""), font=f_prop, fill=col)

    # ── STEP 8: CTA ────────────────────────────────────────────────────────
    cta_y2 = cry_card_y + 162
    img = glow_halo(img, W//2, cta_y2+60, 175, GLOW_TEAL, alpha=22, layers=4)
    draw = ImageDraw.Draw(img)

    sep_ov5 = Image.new("RGBA", (W,H), (0,0,0,0))
    sep_d5 = ImageDraw.Draw(sep_ov5)
    for x in range(W):
        a = int(55 * math.sin(x/W*math.pi))
        sep_d5.point((x, cta_y2-15), fill=(*ACCENT, a))
    img = Image.alpha_composite(img.convert("RGBA"), sep_ov5).convert("RGB")
    draw = ImageDraw.Draw(img)

    img = glass_card(img, 58, cta_y2, W-58, cta_y2+135, radius=20, alpha=62)
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([58, cta_y2, W-58, cta_y2+3], radius=2, fill=ACCENT)

    f_cta_text = F(34, bold=True, serif=True)
    cx_text(draw, cta_text, cta_y2+26, f_cta_text, WHITE)

    f_url = F(23)
    cx_text(draw, cta_url, cta_y2+79, f_url, ACCENT)

    f_foot2 = F(17)
    cx_text(draw, f"✦  {brand}  ·  PHI369 Labs  ✦", cta_y2+112, f_foot2, MUTED)

    # ── STEP 9: VectorFX SVG overlay ──────────────────────────────────────
    if vectorfx_svg_path and Path(vectorfx_svg_path).exists():
        try:
            import cairosvg, io as _io
            svg_bytes = cairosvg.svg2png(url=vectorfx_svg_path, output_width=180, output_height=180)
            svg_img = Image.open(_io.BytesIO(svg_bytes)).convert("RGBA")
            # Position at top center as decorative element
            pos_x = (W-180)//2
            pos_y = 12
            # Apply opacity
            alpha_ch = svg_img.split()[3]
            alpha_ch = alpha_ch.point(lambda p: int(p*0.6))
            svg_img.putalpha(alpha_ch)
            img.paste(svg_img, (pos_x, pos_y), svg_img)
        except Exception as e:
            print(f"  ⚠️  SVG overlay skipped: {e}")

    # ── STEP 10: Final polish ──────────────────────────────────────────────
    img = add_noise(img, intensity=4)
    img = add_vignette(img, strength=50)

    return img


# ── Demo render ───────────────────────────────────────────────────────────────

PHASES_DATA = [
    {"num":1,"name":"SEED",  "days":"Days 1–9", "tag":"Identity Map",      "color":ACCENT,
     "desc":"Who are you becoming? Plant the energetic foundation with daily crystal and journal work."},
    {"num":2,"name":"BUILD", "days":"Days 10–18","tag":"Cycle Intelligence","color":(100,160,255),
     "desc":"Remove friction. Align with solar, lunar, and nervous system cycles."},
    {"num":3,"name":"REVEAL","days":"Days 19–27","tag":"Sacred Refinement", "color":ACCENT2,
     "desc":"Gene Keys. Christos Oil integrity practice. Ancestral wound transformation."},
    {"num":4,"name":"SEAL",  "days":"Days 28–30","tag":"Lock It In",        "color":GOLD,
     "desc":"Ceremony. Sovereign vow. Rhythm Code dashboard signed and sealed."},
]

PRACTICES_DATA = [
    {"icon":"🔮","name":"Crystal","color":ACCENT,"sub":"Stone pairing\n+ intention"},
    {"icon":"✦","name":"Chakra","color":ACCENT2,"sub":"Targeted\naffirmation"},
    {"icon":"🌀","name":"Coherence","color":GOLD,"sub":"Spoken\nvow"},
    {"icon":"📖","name":"Journal","color":(100,160,255),"sub":"4-5 deep\nprompts"},
    {"icon":"🎵","name":"Sound","color":MUTED,"sub":"Solfeggio\nfrequency"},
]

CRYSTALS_DATA = [
    {"name":"Clear\nQuartz","color":ACCENT,"property":"Amplify"},
    {"name":"Citrine","color":(220,180,50),"property":"Abundance"},
    {"name":"Rose\nQuartz","color":(220,140,160),"property":"Heart"},
    {"name":"Amethyst","color":(140,100,200),"property":"Intuition"},
    {"name":"Selenite","color":(200,210,230),"property":"Ceremony"},
]

CHAKRAS_DATA = [
    ((155,89,182),"Crown"), ((74,35,90),"3rd Eye"), ((26,82,118),"Throat"),
    ((30,132,73),"Heart"), ((183,149,11),"Solar"), ((186,74,0),"Sacral"),
    ((146,43,33),"Root"),
]

# Check for AI background (would be passed in real usage)
ai_bg = None  # Replace with generate_background() output when ComfyUI is running

img = render_infographic(
    title="30-Day Sovereign Body",
    subtitle="Crystal · Chakra · Gene Keys · Rhythm Code",
    phases=PHASES_DATA,
    practices=PRACTICES_DATA,
    crystals=CRYSTALS_DATA,
    chakras=CHAKRAS_DATA,
    cta_text="Get the Journal — $27",
    cta_url="microneesia.gumroad.com",
    brand="The Porch is Eternal",
    ai_background_path=ai_bg,
    tags=["Crystal Practices","Chakra Alignment","Gene Keys","Rhythm Code"],
)

out_path = "/mnt/user-data/outputs/SovereignBody_AIReady_Infographic.png"
img.save(out_path, quality=97, dpi=(300,300))
print(f"DONE: {out_path}")
