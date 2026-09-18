"""
EVIE File Handoff Modules
Bridges EVIE with VectorFX and VisionFX via watched folders.

VectorFX Workflow:
  1. EVIE writes a prompt to data/vectorfx_queue/
  2. You open VectorFX, paste the prompt, generate SVG
  3. Save SVG to data/vectorfx_output/
  4. EVIE detects the file and composites it into infographics

VisionFX Workflow:
  1. EVIE saves a finished PNG to data/visionfx_queue/
  2. VisionFX enhances it (image-to-image, style transfer, upscale)
  3. You save the result to data/visionfx_output/
  4. EVIE picks up the enhanced version as the final output

Drop into: D:/EVIEv4.0/app/modules_v2/fx_handoff.py
"""

import os, time, shutil, json
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET


# ── Folder structure ──────────────────────────────────────────────────────────

VECTORFX_QUEUE  = Path("data/vectorfx_queue")
VECTORFX_OUTPUT = Path("data/vectorfx_output")
VISIONFX_QUEUE  = Path("data/visionfx_queue")
VISIONFX_OUTPUT = Path("data/visionfx_output")

for folder in [VECTORFX_QUEUE, VECTORFX_OUTPUT, VISIONFX_QUEUE, VISIONFX_OUTPUT]:
    folder.mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# VECTORFX HANDOFF
# ══════════════════════════════════════════════════════════════════════════════

# Prompt templates optimized for VectorFX's text-to-SVG engine
VECTORFX_PROMPTS = {
    "sacred_geometry": (
        "sacred geometry mandala, flower of life pattern, metatron cube, "
        "geometric circles and triangles, phi spiral, minimal, black lines on white, "
        "clean vector, no fill colors, outline only"
    ),
    "crystal_icon": (
        "crystal gemstone faceted icon, diamond shape, geometric facets, "
        "minimal vector illustration, clean lines, symmetrical, no text"
    ),
    "chakra_symbol": (
        "chakra symbol lotus flower, geometric mandala, sacred circle, "
        "minimal vector, clean lines, symmetrical, spiritual symbol"
    ),
    "phi_spiral": (
        "fibonacci golden ratio spiral, phi proportion, mathematical curve, "
        "precise geometric construction, minimal vector lines, no fill"
    ),
    "wave_pattern": (
        "abstract sound wave pattern, repeating geometric waves, "
        "clean minimal vector, horizontal flow, no text"
    ),
    "logo_mark": (
        "abstract geometric logo mark, sacred geometry inspired, "
        "hexagon and circle composition, minimal, professional, vector"
    ),
    "star_pattern": (
        "sacred geometry star of david, merkaba, geometric star pattern, "
        "interlocking triangles, minimal clean vector lines"
    ),
    "tree_of_life": (
        "tree of life kabbalah symbol, sacred geometry circles connected, "
        "minimal vector, clean geometric lines, spiritual diagram"
    ),
}


def write_vectorfx_prompt(
    element_type: str,
    custom_prompt: str = "",
    job_id: str = "",
    notes: str = ""
) -> str:
    """
    Write a VectorFX prompt file to the queue folder.
    Opens a text file with the prompt — you copy/paste into VectorFX.
    
    Returns: path to the prompt file
    """
    if not job_id:
        job_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    prompt = custom_prompt or VECTORFX_PROMPTS.get(element_type, element_type)

    content = f"""VectorFX Prompt — EVIE Job {job_id}
{"="*50}

ELEMENT TYPE: {element_type}
GENERATED:    {datetime.now().strftime("%Y-%m-%d %H:%M")}

PROMPT TO PASTE INTO VECTORFX:
{"-"*50}
{prompt}
{"-"*50}

INSTRUCTIONS:
1. Open VectorFX on your PC
2. Paste the prompt above into the text field
3. Adjust settings for best quality on your RTX 5070
4. Generate until you have a result you like
5. Save as SVG to:
   D:\\EVIEv4.0\\data\\vectorfx_output\\{element_type}_{job_id}.svg

EVIE will automatically detect and use the SVG file.

NOTES: {notes or "None"}
"""

    prompt_file = VECTORFX_QUEUE / f"prompt_{element_type}_{job_id}.txt"
    prompt_file.write_text(content, encoding="utf-8")
    print(f"  📝 VectorFX prompt written → {prompt_file}")
    print(f"     Open VectorFX and paste the prompt. Save SVG to vectorfx_output/")
    return str(prompt_file)


def wait_for_vectorfx_output(
    filename_pattern: str,
    timeout: int = 300,
    poll_interval: float = 2.0
) -> str | None:
    """
    Wait for a SVG file matching pattern to appear in vectorfx_output/.
    Returns path when found, None on timeout.
    """
    print(f"  ⏳ Waiting for VectorFX output ({filename_pattern})...")
    start = time.time()
    while time.time() - start < timeout:
        matches = list(VECTORFX_OUTPUT.glob(f"*{filename_pattern}*.svg"))
        if matches:
            # Return the most recent match
            latest = max(matches, key=lambda p: p.stat().st_mtime)
            print(f"  ✅ VectorFX output detected: {latest.name}")
            return str(latest)
        time.sleep(poll_interval)
    print(f"  ⚠️  VectorFX timeout — no SVG found after {timeout}s")
    return None


def composite_svg_on_image(
    base_image_path: str,
    svg_path: str,
    output_path: str,
    x: int = 0,
    y: int = 0,
    scale: float = 1.0,
    opacity: float = 0.85
) -> str:
    """
    Composite a VectorFX SVG onto a PIL image.
    Requires: pip install cairosvg
    Falls back to PIL-based SVG rendering if cairosvg unavailable.
    """
    from PIL import Image
    import numpy as np

    try:
        import cairosvg

        # Convert SVG to PNG via cairosvg
        svg_png_bytes = cairosvg.svg2png(
            url=svg_path,
            output_width=int(500 * scale),
            output_height=int(500 * scale),
        )
        svg_img = Image.open(__import__("io").BytesIO(svg_png_bytes)).convert("RGBA")

    except ImportError:
        # Fallback: render as simple placeholder
        print("  ⚠️  cairosvg not installed — SVG compositing unavailable")
        print("      Run: pip install cairosvg --break-system-packages")
        return base_image_path

    base = Image.open(base_image_path).convert("RGBA")

    # Apply opacity
    if opacity < 1.0:
        alpha = svg_img.split()[3]
        alpha = alpha.point(lambda p: int(p * opacity))
        svg_img.putalpha(alpha)

    base.paste(svg_img, (x, y), svg_img)
    base.convert("RGB").save(output_path)
    return output_path


def get_all_vectorfx_outputs() -> list:
    """List all SVG files in the output folder."""
    return [
        {
            "name": p.stem,
            "path": str(p),
            "size_kb": p.stat().st_size // 1024,
            "modified": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        }
        for p in VECTORFX_OUTPUT.glob("*.svg")
    ]


# ══════════════════════════════════════════════════════════════════════════════
# VISIONFX HANDOFF
# ══════════════════════════════════════════════════════════════════════════════

VISIONFX_STYLES = {
    "notebooklm":   "deep space, cosmic, teal and purple, sacred geometry particles, dark moody",
    "wellness":     "soft ethereal glow, golden light, nature inspired, warm sacred light",
    "crystal":      "crystal clear, amethyst purple, iridescent, mystical glow",
    "cinematic":    "cinematic color grade, deep shadows, teal orange complementary, film noir",
    "sacred":       "sacred mystical, golden ratio, ancient wisdom, luminous spiritual",
    "luxury":       "dark luxury, obsidian black, gold accents, premium minimalist",
}

def send_to_visionfx(
    image_path: str,
    style: str = "notebooklm",
    custom_style: str = "",
    job_id: str = ""
) -> str:
    """
    Copy an image to the VisionFX queue with style instructions.
    Returns path to the queued file + writes an instruction file.
    """
    if not job_id:
        job_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    style_prompt = custom_style or VISIONFX_STYLES.get(style, VISIONFX_STYLES["notebooklm"])

    # Copy image to queue
    src = Path(image_path)
    dest = VISIONFX_QUEUE / f"{src.stem}_{job_id}{src.suffix}"
    shutil.copy2(image_path, dest)

    # Write instruction file alongside
    instructions = f"""VisionFX Enhancement Instructions — Job {job_id}
{"="*50}

INPUT FILE:   {dest.name}
STYLE PROMPT: {style_prompt}
STRENGTH:     0.45-0.65 (preserve layout, enhance atmosphere)
STEPS:        25-30
SEED:         random

INSTRUCTIONS:
1. Open VisionFX (standalone or via CorelDRAW plugin)
2. Load the input file from:
   D:\\EVIEv4.0\\data\\visionfx_queue\\{dest.name}
3. Enter this style prompt:
   {style_prompt}
4. Set strength to 0.5 (preserves composition, enhances mood)
5. Click Run — generate 3-5 variations
6. Pick the best result
7. Save to:
   D:\\EVIEv4.0\\data\\visionfx_output\\{src.stem}_{job_id}_enhanced.png

EVIE will automatically detect the enhanced file.

TIP: Lower strength (0.3-0.4) = subtle enhancement
     Higher strength (0.6-0.7) = dramatic transformation
"""

    instr_file = VISIONFX_QUEUE / f"instructions_{job_id}.txt"
    instr_file.write_text(instructions, encoding="utf-8")

    print(f"  📸 Image queued for VisionFX: {dest.name}")
    print(f"     Open VisionFX, load the file, use prompt: '{style_prompt[:60]}...'")
    print(f"     Save enhanced result to visionfx_output/")

    return str(dest)


def wait_for_visionfx_output(
    original_name: str,
    timeout: int = 600,
    poll_interval: float = 3.0
) -> str | None:
    """Wait for enhanced image to appear in visionfx_output/."""
    stem = Path(original_name).stem.split("_")[0]  # base name without job_id
    print(f"  ⏳ Waiting for VisionFX enhanced output...")

    start = time.time()
    while time.time() - start < timeout:
        matches = list(VISIONFX_OUTPUT.glob(f"*{stem}*enhanced*.png"))
        if matches:
            latest = max(matches, key=lambda p: p.stat().st_mtime)
            print(f"  ✅ VisionFX output: {latest.name}")
            return str(latest)
        time.sleep(poll_interval)

    print(f"  ⚠️  VisionFX timeout after {timeout}s — using original")
    return None


def enhance_or_fallback(
    image_path: str,
    style: str = "notebooklm",
    wait: bool = False,
    timeout: int = 300
) -> str:
    """
    Send to VisionFX queue. If wait=True, block until enhanced version is ready.
    Otherwise returns original path immediately (async workflow).
    """
    queued_path = send_to_visionfx(image_path, style)

    if wait:
        enhanced = wait_for_visionfx_output(queued_path, timeout=timeout)
        return enhanced or image_path

    return image_path  # Return original, enhanced version comes later


# ══════════════════════════════════════════════════════════════════════════════
# EVIE STATUS DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

def fx_status() -> dict:
    """
    Returns status of all FX queues and outputs.
    Call this from EVIE dashboard to see pending jobs.
    """
    return {
        "vectorfx": {
            "queue_count":  len(list(VECTORFX_QUEUE.glob("*.txt"))),
            "output_count": len(list(VECTORFX_OUTPUT.glob("*.svg"))),
            "outputs": [p.name for p in VECTORFX_OUTPUT.glob("*.svg")],
        },
        "visionfx": {
            "queue_count":  len(list(VISIONFX_QUEUE.glob("*.png"))),
            "output_count": len(list(VISIONFX_OUTPUT.glob("*.png"))),
            "outputs": [p.name for p in VISIONFX_OUTPUT.glob("*.png")],
        },
    }


def clear_queues():
    """Clear all queue folders (run after processing)."""
    for folder in [VECTORFX_QUEUE, VISIONFX_QUEUE]:
        for f in folder.iterdir():
            f.unlink()
    print("✅ FX queues cleared")
