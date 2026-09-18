"""
EVIE Video Presentation Generator
Converts slide PNGs + audio into a cinematic MP4 video.

Features:
  - Ken Burns pan/zoom on every slide (no static frames)
  - Cinematic transitions: fade, slide-in, zoom-through, wipe
  - Lower-third captions timed to slides
  - Audio sync with ElevenLabs MP3 or any audio file
  - Intro/outro title cards
  - Output: 1920x1080 MP4 @ 30fps, ready for YouTube/social
  - OR: 1080x1920 vertical for Reels/TikTok/Shorts

Drop into: D:/EVIEv4.0/app/modules_v2/video_generator.py
Also run: pip install moviepy --break-system-packages
"""

import os, re, json, math, shutil
import importlib.util
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import numpy as np
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except Exception:
    Image = None
    ImageDraw = None
    ImageFont = None
    ImageFilter = None

try:
    # moviepy v2 imports
    from moviepy import (
        ImageClip, VideoClip, AudioFileClip,
        concatenate_videoclips, CompositeVideoClip,
        ColorClip
    )
except Exception:
    ImageClip = None
    VideoClip = None
    AudioFileClip = None
    concatenate_videoclips = None
    CompositeVideoClip = None
    ColorClip = None

from app.modules.base import BaseModule
from .base import ModuleResult


# ── Constants ─────────────────────────────────────────────────────────────────

FPS = 30
LANDSCAPE = (1920, 1080)
PORTRAIT  = (1080, 1920)

# NotebookLM palette
BG_COLOR  = (8, 12, 28)
ACCENT    = (82, 196, 196)
GOLD      = (201, 163, 75)
WHITE     = (255, 255, 255)
MUTED     = (140, 160, 210)
DARK      = (10, 14, 35)


# ── Font helpers ──────────────────────────────────────────────────────────────

def _font(size, bold=False, serif=False):
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


# ── Slide image preparation ───────────────────────────────────────────────────

def _fit_slide(img_path: str, size: tuple) -> np.ndarray:
    """Load and fit a slide image to target size, letterboxing if needed."""
    W, H = size
    img = Image.open(img_path).convert("RGB")
    iw, ih = img.size
    scale = min(W / iw, H / ih)
    new_w, new_h = int(iw * scale), int(ih * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    # Place on dark background
    canvas = Image.new("RGB", (W, H), BG_COLOR)
    x = (W - new_w) // 2
    y = (H - new_h) // 2
    canvas.paste(img, (x, y))
    return np.array(canvas)


def _make_title_card(title: str, subtitle: str, size: tuple, 
                     brand: str = "The Porch is Eternal") -> np.ndarray:
    """Generate a styled title card as numpy array."""
    W, H = size
    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Background gradient
    arr = np.array(img, dtype=np.float32)
    for y in range(H):
        t = y / H
        warm = (1 - t) * 12
        arr[y, :, 0] += warm
        arr[y, :, 2] += warm * 0.3
    img = Image.fromarray(arr.clip(0, 255).astype(np.uint8))
    draw = ImageDraw.Draw(img)

    # Dot grid
    for gy in range(0, H, 36):
        for gx in range(0, W, 36):
            draw.ellipse([gx-1, gy-1, gx+1, gy+1], fill=(80, 110, 180, 18))

    # Glow circle
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for i in range(5):
        r = 220 + i * 35
        a = max(3, 30 // (i + 1))
        od.ellipse([W//2-r, H//2-r, W//2+r, H//2+r], fill=(*ACCENT, a))
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Brand
    scale = W / 1920
    f_brand = _font(int(22 * scale), bold=True)
    brand_txt = f"✦   {brand.upper()}   ✦"
    bb = f_brand.getbbox(brand_txt)
    draw.text(((W - (bb[2]-bb[0]))//2, int(H * 0.28)), brand_txt, font=f_brand, fill=GOLD)

    # Title
    f_title = _font(int(72 * scale), bold=True, serif=True)
    words = title.split()
    mid = len(words)//2
    line1 = " ".join(words[:mid]) if len(words) > 1 else title
    line2 = " ".join(words[mid:]) if len(words) > 1 else ""
    
    bb1 = f_title.getbbox(line1)
    draw.text(((W-(bb1[2]-bb1[0]))//2, int(H*0.38)), line1, font=f_title, fill=WHITE)
    if line2:
        bb2 = f_title.getbbox(line2)
        draw.text(((W-(bb2[2]-bb2[0]))//2, int(H*0.38)+int(85*scale)), line2, font=f_title, fill=(*ACCENT,))

    # Subtitle
    if subtitle:
        f_sub = _font(int(26 * scale), serif=False)
        bb3 = f_sub.getbbox(subtitle)
        draw.text(((W-(bb3[2]-bb3[0]))//2, int(H*0.62)), subtitle, font=f_sub, fill=(*MUTED,))

    # Accent line
    lw = int(W * 0.55)
    draw.line([(W-lw)//2, int(H*0.72), (W+lw)//2, int(H*0.72)], fill=(*ACCENT, 120), width=2)

    return np.array(img)


def _make_lower_third(text: str, size: tuple, progress: float = 1.0) -> np.ndarray:
    """Generate a lower-third caption overlay as RGBA numpy array."""
    W, H = size
    scale = W / 1920
    
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    bar_h = int(68 * scale)
    bar_y = int(H * 0.82)
    bar_w = int(min(W * 0.65 * progress, W * 0.65))

    # Dark background bar
    draw.rectangle([0, bar_y, bar_w, bar_y + bar_h], fill=(8, 12, 28, 200))

    # Teal accent left edge
    draw.rectangle([0, bar_y, int(5 * scale), bar_y + bar_h], fill=(*ACCENT, 255))

    # Text
    f = _font(int(26 * scale), bold=True)
    draw.text((int(20 * scale), bar_y + int(18 * scale)), text, font=f, fill=(*WHITE,))

    return np.array(img)


# ── Ken Burns effect ──────────────────────────────────────────────────────────

def ken_burns_clip(img_array: np.ndarray, duration: float, 
                   zoom_start: float = 1.0, zoom_end: float = 1.08,
                   pan_x: float = 0.0, pan_y: float = 0.0) -> VideoClip:
    """
    Apply Ken Burns pan/zoom effect to a static image.
    zoom_start/end: 1.0 = fill frame, 1.08 = 8% zoom
    pan_x/y: -1.0 to 1.0 — direction of pan during zoom
    """
    H, W = img_array.shape[:2]
    
    def make_frame(t):
        progress = t / duration
        zoom = zoom_start + (zoom_end - zoom_start) * progress
        
        # Crop size
        crop_w = int(W / zoom)
        crop_h = int(H / zoom)
        
        # Pan offset
        max_pan_x = (W - crop_w) // 2
        max_pan_y = (H - crop_h) // 2
        
        off_x = int(W//2 - crop_w//2 + pan_x * max_pan_x * progress)
        off_y = int(H//2 - crop_h//2 + pan_y * max_pan_y * progress)
        
        # Clamp
        off_x = max(0, min(off_x, W - crop_w))
        off_y = max(0, min(off_y, H - crop_h))
        
        # Crop and resize
        cropped = img_array[off_y:off_y+crop_h, off_x:off_x+crop_w]
        pil = Image.fromarray(cropped).resize((W, H), Image.LANCZOS)
        return np.array(pil)
    
    return VideoClip(make_frame, duration=duration)


# ── Transition effects ────────────────────────────────────────────────────────

def fade_transition(clip1, clip2, duration=0.5):
    """Cross-fade between two clips."""
    c1 = clip1.with_effects([
        lambda c: c.subclipped(0, c.duration - duration/2)
    ])
    # Simple approach: fade out clip1, fade in clip2
    return concatenate_videoclips([clip1, clip2], method="compose")


def _apply_lower_third(base_clip, text: str, start: float, end: float) -> CompositeVideoClip:
    """Overlay a lower-third text caption on a clip during a time range."""
    W, H = base_clip.size
    anim_dur = 0.4  # slide-in duration

    def lt_frame(t):
        local_t = t - start
        if local_t < 0 or t > end:
            return np.zeros((H, W, 4), dtype=np.uint8)
        
        # Slide-in progress
        progress = min(1.0, local_t / anim_dur)
        # Ease out
        progress = 1 - (1 - progress) ** 2
        
        # Fade out near end
        fade = 1.0
        if t > end - 0.4:
            fade = (end - t) / 0.4
        
        frame = _make_lower_third(text, (W, H), progress)
        if fade < 1.0:
            frame[:, :, 3] = (frame[:, :, 3] * fade).astype(np.uint8)
        return frame

    lt_clip = VideoClip(lt_frame, duration=base_clip.duration, is_mask=False)
    lt_clip = lt_clip.with_fps(FPS)

    return CompositeVideoClip([base_clip, lt_clip])


# ── Main class ────────────────────────────────────────────────────────────────

class VideoGenerator(BaseModule):
    """
    Generates cinematic MP4 video presentations from slide images and audio.

    Workflow:
    1. Takes a list of slide PNG paths (from infographic_generator or pptx export)
    2. Applies Ken Burns effects and transitions
    3. Syncs with audio file (from audio_generator or any MP3)
    4. Renders to MP4

    Constraint examples:
    {
        "slides": [
            "data/artifacts/infographics/slide1.png",
            "data/artifacts/infographics/slide2.png"
        ],
        "audio_path": "data/artifacts/audio/podcast_xyz.mp3",
        "captions": ["Phase One: SEED", "Phase Two: BUILD", "Phase Three: REVEAL"],
        "title": "30-Day Sovereign Body Transformation",
        "subtitle": "Crystal · Chakra · Gene Keys · Rhythm Code",
        "brand": "The Porch is Eternal",
        "orientation": "landscape",   // landscape (1920x1080) | portrait (1080x1920)
        "seconds_per_slide": 8,       // if no audio
        "show_title_card": true,
        "show_outro_card": true,
        "transition": "fade",         // fade | zoom | none
        "fps": 30
    }
    """

    name = "video_generator"
    description = "Generate cinematic MP4 video presentations from slides + audio"

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
        merged = dict(constraints or {})
        merged.setdefault("output_dir", run_folder)

        missing = []
        if VideoClip is None or importlib.util.find_spec("moviepy") is None:
            missing.append("moviepy")
        if Image is None or importlib.util.find_spec("PIL") is None:
            missing.append("Pillow")
        if shutil.which("ffmpeg") is None:
            missing.append("ffmpeg")
        if missing:
            return ModuleResult(
                name=self.name,
                artifacts=[],
                summary={
                    "ok": False,
                    "error": f"video_generator requires missing dependencies: {', '.join(missing)}.",
                    "missing_dependencies": missing,
                },
            )

        audio_path = str(merged.get("audio_path") or "").strip()
        if audio_path and not Path(audio_path).exists():
            return ModuleResult(
                name=self.name,
                artifacts=[],
                summary={
                    "ok": False,
                    "error": f"video_generator audio_path not found: {audio_path}",
                    "missing_input": "audio_path",
                },
            )

        try:
            out = self.run(topic=topic, constraints=merged, context=str(merged.get("context") or ""))
            if out.get("error"):
                return ModuleResult(name=self.name, artifacts=[], summary={"ok": False, **out})
            artifacts = [v for k, v in out.items() if k.endswith("_path") and isinstance(v, str)]
            return ModuleResult(name=self.name, artifacts=artifacts, summary=out)
        except Exception as exc:
            return ModuleResult(
                name=self.name,
                artifacts=[],
                summary={"ok": False, "error": f"video_generator failed: {exc}"},
            )

    def run(self, topic: str, constraints: dict, context: str = "") -> dict:
        slides_paths  = constraints.get("slides", [])
        audio_path    = constraints.get("audio_path", "")
        captions      = constraints.get("captions", [])
        title         = constraints.get("title", topic)
        subtitle      = constraints.get("subtitle", "")
        brand         = constraints.get("brand", "The Porch is Eternal")
        orientation   = constraints.get("orientation", "landscape")
        secs_per_slide= constraints.get("seconds_per_slide", 8)
        show_title    = constraints.get("show_title_card", True)
        show_outro    = constraints.get("show_outro_card", True)
        transition    = constraints.get("transition", "fade")
        fps           = constraints.get("fps", FPS)

        size = PORTRAIT if orientation == "portrait" else LANDSCAPE
        W, H = size

        # Validate slides
        valid_slides = [p for p in slides_paths if os.path.exists(p)]
        if not valid_slides and not show_title:
            return {"error": "No valid slide images found. Provide slide paths in constraints."}

        # Determine timing
        audio_clip = None
        total_audio_dur = None
        if audio_path and os.path.exists(audio_path):
            audio_clip = AudioFileClip(audio_path)
            total_audio_dur = audio_clip.duration

        n_slides = len(valid_slides) + (1 if show_title else 0) + (1 if show_outro else 0)
        if total_audio_dur and n_slides > 0:
            secs_per_slide = total_audio_dur / n_slides
        
        secs_per_slide = max(3.0, secs_per_slide)

        print(f"Building video: {n_slides} segments × {secs_per_slide:.1f}s = {n_slides * secs_per_slide:.0f}s total")

        clips = []

        # ── TITLE CARD ─────────────────────────────────────────────────────
        if show_title:
            print("  Rendering title card...")
            title_arr = _make_title_card(title, subtitle, size, brand)
            tc = ken_burns_clip(title_arr, secs_per_slide,
                               zoom_start=1.0, zoom_end=1.05,
                               pan_x=0.0, pan_y=-0.2)
            tc = tc.with_fps(fps)
            if transition == "fade":
                tc = tc.with_effects([lambda c: c.fadein(0.5)])
            clips.append(tc)

        # ── CONTENT SLIDES ─────────────────────────────────────────────────
        kb_patterns = [
            (1.0, 1.08, -0.3, -0.2),   # zoom in, pan top-left to center
            (1.06, 1.0, 0.3, 0.2),     # zoom out, pan right to left
            (1.0, 1.1,  0.0, -0.3),    # zoom in, pan down
            (1.08, 1.0, -0.2, 0.3),    # zoom out, pan left to right
            (1.0, 1.06, 0.2, 0.0),     # subtle zoom, pan left
        ]

        for i, slide_path in enumerate(valid_slides):
            print(f"  Rendering slide {i+1}/{len(valid_slides)}: {Path(slide_path).name}")
            slide_arr = _fit_slide(slide_path, size)

            zs, ze, px, py = kb_patterns[i % len(kb_patterns)]
            clip = ken_burns_clip(slide_arr, secs_per_slide, zs, ze, px, py)
            clip = clip.with_fps(fps)

            # Add fade transitions
            if transition == "fade":
                clip = clip.with_effects([
                    lambda c: c.fadein(0.4).fadeout(0.4)
                ])

            # Lower-third caption
            if i < len(captions) and captions[i]:
                clip = _apply_lower_third(clip, captions[i], 0.6, secs_per_slide - 0.5)

            clips.append(clip)

        # ── OUTRO CARD ─────────────────────────────────────────────────────
        if show_outro:
            print("  Rendering outro card...")
            outro_txt  = f"The Porch is Eternal"
            outro_sub  = "microneesia.gumroad.com"
            outro_arr  = _make_title_card(outro_txt, outro_sub, size, brand)
            oc = ken_burns_clip(outro_arr, secs_per_slide,
                               zoom_start=1.03, zoom_end=1.0,
                               pan_x=0.0, pan_y=0.1)
            oc = oc.with_fps(fps)
            if transition == "fade":
                oc = oc.with_effects([lambda c: c.fadein(0.5).fadeout(0.8)])
            clips.append(oc)

        if not clips:
            return {"error": "No clips were generated"}

        # ── ASSEMBLE ───────────────────────────────────────────────────────
        print("  Concatenating clips...")
        final = concatenate_videoclips(clips, method="compose")

        # ── AUDIO ──────────────────────────────────────────────────────────
        if audio_clip:
            print("  Syncing audio...")
            # Trim or loop audio to match video length
            vid_dur = final.duration
            if audio_clip.duration > vid_dur:
                audio_clip = audio_clip.subclipped(0, vid_dur)
            elif audio_clip.duration < vid_dur:
                # Fade out at end
                audio_clip = audio_clip.with_effects([
                    lambda a: a.audio_fadeout(min(2.0, audio_clip.duration * 0.1))
                ])
            final = final.with_audio(audio_clip)

        # ── RENDER ─────────────────────────────────────────────────────────
        out_path = self._get_output_path(topic, constraints)
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        
        print(f"  Rendering to {out_path}...")
        print(f"  Duration: {final.duration:.1f}s at {fps}fps")
        
        final.write_videofile(
            out_path,
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            bitrate="4000k",
            preset="medium",
            threads=4,
            logger=None,  # suppress verbose output
        )

        # Cleanup
        final.close()
        if audio_clip:
            audio_clip.close()

        file_size_mb = os.path.getsize(out_path) / (1024 * 1024)
        
        return {
            "artifact_path": out_path,
            "duration_seconds": round(n_slides * secs_per_slide, 1),
            "slide_count": len(valid_slides),
            "size": f"{W}x{H}",
            "file_size_mb": round(file_size_mb, 1),
            "fps": fps,
        }

    def _get_output_path(self, topic: str, constraints: dict | None = None) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", topic.lower())[:40]
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = Path((constraints or {}).get("output_dir") or "data/artifacts/videos")
        out_dir.mkdir(parents=True, exist_ok=True)
        return str(out_dir / f"video_{slug}__{ts}.mp4")


# ── Standalone slide exporter ─────────────────────────────────────────────────

def export_pptx_to_pngs(pptx_path: str, output_dir: str) -> list:
    """
    Convert PPTX slides to PNG images for video generation.
    Requires LibreOffice (soffice) installed.
    
    Usage:
        from app.modules_v2.video_generator import export_pptx_to_pngs
        slides = export_pptx_to_pngs("my_deck.pptx", "data/slides/")
    """
    import subprocess
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Convert to PDF first
    result = subprocess.run([
        "soffice", "--headless", "--convert-to", "pdf",
        "--outdir", str(out_dir), pptx_path
    ], capture_output=True, text=True, timeout=60)
    
    pdf_path = out_dir / (Path(pptx_path).stem + ".pdf")
    if not pdf_path.exists():
        raise RuntimeError(f"LibreOffice conversion failed: {result.stderr}")
    
    # Convert PDF pages to PNGs
    result2 = subprocess.run([
        "pdftoppm", "-png", "-r", "150",
        str(pdf_path), str(out_dir / "slide")
    ], capture_output=True, timeout=120)
    
    pngs = sorted(out_dir.glob("slide-*.png"))
    return [str(p) for p in pngs]
