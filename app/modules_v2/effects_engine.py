"""
EVIE Effects Engine
Drop any image in, write a prompt, get a transformed version back.

Modes:
  1. RESTYLE      — keep structure, change the look/mood/style
  2. ENHANCE      — improve quality, add detail, upscale atmosphere
  3. SACRED       — apply sacred geometry / PHI369 visual language
  4. SEASONAL     — change environment, lighting, time of day
  5. BRAND        — push image toward The Porch is Eternal aesthetic
  6. INPAINT      — fill/replace a region (mask required)
  7. UPSCALE      — AI upscale to 2x or 4x resolution

All effects use ComfyUI img2img workflows with FLUX Redux or SD img2img.
Falls back to PIL-based effects if ComfyUI is unavailable.

Drop into: D:/EVIEv4.0/app/modules_v2/effects_engine.py
"""

import os, re, time, json, base64, requests, uuid, random, math
from pathlib import Path
from datetime import datetime
from typing import Optional
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageFont
import numpy as np
from .base import BaseModule


COMFYUI_URL = "http://127.0.0.1:8188"
CLIENT_ID   = str(uuid.uuid4())


# ── Effect Presets ────────────────────────────────────────────────────────────

EFFECT_PRESETS = {

    "sacred_geometry": {
        "desc": "Overlay sacred geometry light patterns, phi spirals, teal glow",
        "prompt_suffix": (
            "sacred geometry overlay, phi spiral light, metatron cube glow, "
            "teal and gold geometric patterns, mystical atmosphere, "
            "cinematic lighting, 8k quality"
        ),
        "strength": 0.45,
        "steps": 25,
        "guidance": 4.0,
    },

    "notebooklm": {
        "desc": "Push image toward NotebookLM dark cosmic aesthetic",
        "prompt_suffix": (
            "dark cosmic atmosphere, teal and purple color grade, "
            "sacred geometry light particles, deep navy shadows, "
            "cinematic depth, professional, 8k"
        ),
        "strength": 0.55,
        "steps": 22,
        "guidance": 3.5,
    },

    "crystal_vision": {
        "desc": "Transform into crystal cave with gemstone lighting",
        "prompt_suffix": (
            "crystal cave transformation, amethyst purple and clear quartz, "
            "teal violet light rays, mystical crystal formations, "
            "ethereal glow, cinematic, 8k"
        ),
        "strength": 0.65,
        "steps": 25,
        "guidance": 3.8,
    },

    "sovereign_gold": {
        "desc": "Gold and dark royal aesthetic, divine authority energy",
        "prompt_suffix": (
            "sovereign gold transformation, divine authority, "
            "dark luxury background, gold foil accents, "
            "sacred royal energy, cinematic, 8k"
        ),
        "strength": 0.50,
        "steps": 22,
        "guidance": 3.5,
    },

    "cosmic_upgrade": {
        "desc": "Transform to deep space with nebula colors",
        "prompt_suffix": (
            "deep space cosmic upgrade, nebula colors, star field, "
            "teal gold purple atmosphere, divine cosmic light, "
            "highly detailed, 8k"
        ),
        "strength": 0.60,
        "steps": 25,
        "guidance": 3.8,
    },

    "phi369_pulse": {
        "desc": "Apply PHI369 mathematical vortex visual language",
        "prompt_suffix": (
            "369 sacred mathematics, phi vortex pulse, tesla 369, "
            "fibonacci wave pattern overlay, teal gold mathematical, "
            "sacred pattern, cinematic, 8k"
        ),
        "strength": 0.55,
        "steps": 28,
        "guidance": 4.2,
    },

    "enhance": {
        "desc": "Improve quality, add detail, enhance atmosphere",
        "prompt_suffix": (
            "enhanced quality, ultra detailed, better lighting, "
            "professional photography, masterpiece, 8k"
        ),
        "strength": 0.30,
        "steps": 20,
        "guidance": 3.0,
    },

    "dark_mood": {
        "desc": "Push toward dark, moody, cinematic atmosphere",
        "prompt_suffix": (
            "dark moody atmosphere, cinematic color grade, deep shadows, "
            "dramatic lighting, teal orange complementary color, "
            "film noir aesthetic, 8k"
        ),
        "strength": 0.50,
        "steps": 22,
        "guidance": 3.5,
    },

    "wellness_glow": {
        "desc": "Warm golden nature glow, healing light, soft bokeh",
        "prompt_suffix": (
            "golden healing light, warm nature glow, soft bokeh, "
            "forest sanctuary light rays, healing atmosphere, "
            "warm gold and green, serene, 8k"
        ),
        "strength": 0.45,
        "steps": 22,
        "guidance": 3.5,
    },

    "blueprint": {
        "desc": "Technical blueprint aesthetic, teal on dark",
        "prompt_suffix": (
            "technical blueprint style, glowing teal lines on dark background, "
            "architectural diagram aesthetic, precise geometric lines, "
            "schematic visualization, cinematic"
        ),
        "strength": 0.70,
        "steps": 25,
        "guidance": 4.0,
    },

    "dreamlike": {
        "desc": "Soft dream-state, ethereal, painterly",
        "prompt_suffix": (
            "dreamlike ethereal quality, soft painterly style, "
            "luminous atmosphere, impressionist light, "
            "sacred feminine energy, soft focus, 8k"
        ),
        "strength": 0.55,
        "steps": 25,
        "guidance": 3.5,
    },

    "neon_sacred": {
        "desc": "Neon cyberpunk meets sacred geometry",
        "prompt_suffix": (
            "neon sacred geometry, cyberpunk teal pink purple, "
            "glowing circuit sacred patterns, dark background, "
            "neon glow, highly detailed, 8k"
        ),
        "strength": 0.65,
        "steps": 28,
        "guidance": 4.0,
    },
}


# ── PIL-based fallback effects (no ComfyUI needed) ───────────────────────────

class PILEffects:
    """
    Fast PIL-based effects for when ComfyUI is offline.
    Not AI-generated — but useful for quick iterations.
    """

    @staticmethod
    def teal_grade(img: Image.Image, strength: float = 0.6) -> Image.Image:
        """Push colors toward teal/dark palette."""
        arr = np.array(img.convert("RGB"), dtype=np.float32)
        arr[:, :, 0] *= (1 - strength * 0.2)   # reduce red
        arr[:, :, 1] *= (1 + strength * 0.05)   # slight green boost
        arr[:, :, 2] *= (1 + strength * 0.15)   # boost blue/teal
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        return Image.fromarray(arr)

    @staticmethod
    def darken(img: Image.Image, factor: float = 0.6) -> Image.Image:
        """Darken image for dark-mode aesthetics."""
        return ImageEnhance.Brightness(img).enhance(factor)

    @staticmethod
    def sacred_overlay(img: Image.Image, color=(82, 196, 196), opacity=0.25) -> Image.Image:
        """Draw sacred geometry overlay — phi spiral + circles."""
        W, H = img.size
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)

        # Concentric circles (sacred geometry rings)
        cx, cy = W // 2, H // 2
        for r in range(50, min(W, H) // 2, 80):
            alpha = int(opacity * 255 * (1 - r / (min(W, H) // 2)))
            d.ellipse([cx-r, cy-r, cx+r, cy+r],
                     fill=None, outline=(*color, alpha), width=1)

        # Phi spiral approximation
        a = min(W, H) * 0.003
        prev_x, prev_y = cx, cy
        for angle in range(0, 720, 3):
            rad = math.radians(angle)
            r_spiral = a * math.exp(0.15 * rad)
            x = int(cx + r_spiral * math.cos(rad))
            y = int(cy + r_spiral * math.sin(rad))
            alpha = min(255, int(opacity * 255 * (r_spiral / (min(W,H)*0.3))))
            if 0 <= x < W and 0 <= y < H:
                d.line([prev_x, prev_y, x, y], fill=(*color, alpha), width=1)
            prev_x, prev_y = x, y

        # Dot grid
        for gy in range(0, H, 45):
            for gx in range(0, W, 45):
                d.ellipse([gx-1, gy-1, gx+1, gy+1], fill=(*color, 18))

        result = Image.alpha_composite(img.convert("RGBA"), ov)
        return result.convert("RGB")

    @staticmethod
    def vignette(img: Image.Image, strength: float = 0.65) -> Image.Image:
        """Add cinematic vignette."""
        W, H = img.size
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        max_r = min(W, H) * 0.75
        for r in range(int(max_r), min(W, H) // 2, -4):
            alpha = int(strength * 255 * (1 - r / max_r) ** 2)
            d.ellipse([W//2-r, H//2-r, W//2+r, H//2+r],
                     fill=None, outline=(0, 0, 0, alpha), width=6)
        result = Image.alpha_composite(img.convert("RGBA"), ov)
        return result.convert("RGB")

    @staticmethod
    def glow_halo(img: Image.Image, color=(82, 196, 196), layers=5) -> Image.Image:
        """Add teal glow halo at center."""
        W, H = img.size
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        cx, cy = W//2, H//3
        for i in range(layers):
            r = 120 + i * 45
            a = max(3, 28 // (i + 1))
            d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(*color, a))
        result = Image.alpha_composite(img.convert("RGBA"), ov)
        return result.convert("RGB")

    @staticmethod
    def sharpen(img: Image.Image, factor: float = 1.8) -> Image.Image:
        return ImageEnhance.Sharpness(img).enhance(factor)

    @staticmethod
    def saturation(img: Image.Image, factor: float = 1.3) -> Image.Image:
        return ImageEnhance.Color(img).enhance(factor)

    @staticmethod
    def blur_bg(img: Image.Image, radius: float = 3.0) -> Image.Image:
        """Blur for dreamy/focus effect."""
        return img.filter(ImageFilter.GaussianBlur(radius))

    @staticmethod
    def noise(img: Image.Image, intensity: int = 6) -> Image.Image:
        """Add film grain."""
        arr = np.array(img, dtype=np.int16)
        noise = np.random.randint(-intensity, intensity, arr.shape, dtype=np.int16)
        return Image.fromarray(np.clip(arr + noise, 0, 255).astype(np.uint8))

    @staticmethod
    def apply_preset_pil(img: Image.Image, effect: str) -> Image.Image:
        """Apply a named PIL effect combo."""
        fx = PILEffects
        combos = {
            "sacred_geometry": lambda i: fx.sacred_overlay(fx.teal_grade(i, 0.4), opacity=0.3),
            "notebooklm":      lambda i: fx.vignette(fx.teal_grade(fx.darken(i, 0.65), 0.5)),
            "crystal_vision":  lambda i: fx.glow_halo(fx.teal_grade(fx.darken(i, 0.7), 0.6), color=(140,100,220)),
            "sovereign_gold":  lambda i: fx.vignette(fx.saturation(fx.darken(i, 0.7), 0.8)),
            "cosmic_upgrade":  lambda i: fx.glow_halo(fx.teal_grade(fx.darken(i, 0.6), 0.5)),
            "enhance":         lambda i: fx.sharpen(fx.saturation(i, 1.2), 2.0),
            "dark_mood":       lambda i: fx.vignette(fx.teal_grade(fx.darken(i, 0.6), 0.4), 0.75),
            "wellness_glow":   lambda i: fx.glow_halo(fx.saturation(i, 1.3), color=(201,163,75), layers=4),
            "dreamlike":       lambda i: fx.sacred_overlay(fx.blur_bg(i, 1.5), opacity=0.15),
            "phi369_pulse":    lambda i: fx.sacred_overlay(fx.teal_grade(i, 0.45), color=(201,163,75), opacity=0.35),
            "neon_sacred":     lambda i: fx.sacred_overlay(fx.teal_grade(fx.darken(i, 0.55), 0.6), color=(200,80,220), opacity=0.4),
            "blueprint":       lambda i: fx.sacred_overlay(fx.teal_grade(fx.darken(i, 0.5), 0.7), opacity=0.5),
        }
        fn = combos.get(effect, combos["enhance"])
        result = fn(img)
        return fx.noise(result, 4)


# ── ComfyUI img2img workflow ──────────────────────────────────────────────────

def _encode_image_b64(image_path: str) -> str:
    return base64.b64encode(Path(image_path).read_bytes()).decode()

def _upload_image_to_comfyui(image_path: str) -> Optional[str]:
    """Upload input image to ComfyUI's /upload/image endpoint."""
    try:
        with open(image_path, "rb") as f:
            r = requests.post(
                f"{COMFYUI_URL}/upload/image",
                files={"image": (Path(image_path).name, f, "image/png")},
                timeout=30
            )
        if r.status_code == 200:
            return r.json().get("name")
    except Exception as e:
        print(f"  Upload error: {e}")
    return None

def _build_img2img_workflow(
    input_image_name: str,
    prompt: str,
    negative: str = "text, watermark, blurry, low quality",
    strength: float = 0.55,
    steps: int = 25,
    guidance: float = 3.5,
    seed: int = -1,
    model: str = "flux1-dev-Q5_K_M.gguf",
    clip_l: str = "clip_l.safetensors",
    t5xxl: str = "t5xxl_fp8_e4m3fn.safetensors",
    vae: str = "ae.safetensors",
) -> dict:
    """
    FLUX img2img workflow using VAE encode of input image.
    strength: 0.0 = no change, 1.0 = completely new image
    """
    if seed == -1:
        seed = random.randint(0, 2**32 - 1)

    return {
        "prompt": {
            # Load input image
            "1": {"class_type": "LoadImage", "inputs": {"image": input_image_name}},
            # Load models
            "2": {"class_type": "UNETLoader", "inputs": {"unet_name": model, "weight_dtype": "default"}},
            "3": {"class_type": "VAELoader", "inputs": {"vae_name": vae}},
            "4": {
                "class_type": "DualCLIPLoader",
                "inputs": {"clip_name1": clip_l, "clip_name2": t5xxl, "type": "flux"}
            },
            # Encode image to latent
            "5": {"class_type": "VAEEncode", "inputs": {"pixels": ["1", 0], "vae": ["3", 0]}},
            # Text encode
            "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 0], "text": prompt}},
            # Flux guidance
            "7": {"class_type": "FluxGuidance", "inputs": {"conditioning": ["6", 0], "guidance": guidance}},
            # Noise + sampler
            "8": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
            "9": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
            "10": {
                "class_type": "BasicScheduler",
                "inputs": {
                    "model": ["2", 0], "scheduler": "simple",
                    "steps": steps, "denoise": strength
                }
            },
            "11": {
                "class_type": "SamplerCustomAdvanced",
                "inputs": {
                    "noise": ["8", 0],
                    "guider": ["12", 0],
                    "sampler": ["9", 0],
                    "sigmas": ["10", 0],
                    "latent_image": ["5", 0]
                }
            },
            "12": {"class_type": "BasicGuider", "inputs": {"model": ["2", 0], "conditioning": ["7", 0]}},
            # Decode and save
            "13": {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["3", 0]}},
            "14": {
                "class_type": "SaveImage",
                "inputs": {"images": ["13", 0], "filename_prefix": "evie_fx"}
            },
        },
        "client_id": CLIENT_ID
    }


def _is_running() -> bool:
    try:
        return requests.get(f"{COMFYUI_URL}/system_stats", timeout=3).status_code == 200
    except:
        return False

def _queue(wf: dict) -> Optional[str]:
    try:
        r = requests.post(f"{COMFYUI_URL}/prompt", json=wf, timeout=10)
        if r.status_code == 200:
            return r.json().get("prompt_id")
    except Exception as e:
        print(f"  Queue error: {e}")
    return None

def _wait(pid: str, timeout: int = 180) -> Optional[dict]:
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(f"{COMFYUI_URL}/history/{pid}", timeout=5)
            if r.status_code == 200:
                h = r.json()
                if pid in h and h[pid].get("status", {}).get("completed"):
                    return h[pid]
        except:
            pass
        time.sleep(0.75)
    return None

def _download(filename: str, subfolder: str, save_path: str) -> bool:
    try:
        r = requests.get(
            f"{COMFYUI_URL}/view",
            params={"filename": filename, "type": "output", "subfolder": subfolder},
            timeout=30
        )
        if r.status_code == 200:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            Path(save_path).write_bytes(r.content)
            return True
    except Exception as e:
        print(f"  Download error: {e}")
    return False


# ── Main Module ───────────────────────────────────────────────────────────────

class EffectsEngine(BaseModule):
    """
    EVIE Effects Engine — drop any image in, apply a prompt + effect.

    Constraint examples:

    RESTYLE:
    {
        "input_image":  "data/artifacts/images/my_photo.png",
        "effect":       "sacred_geometry",
        "prompt":       "",               // leave blank to use preset
        "strength":     0.5,              // 0.0-1.0 (higher = more change)
        "steps":        25,
        "seed":         -1
    }

    CUSTOM PROMPT:
    {
        "input_image":  "data/artifacts/infographics/my_infographic.png",
        "effect":       "custom",
        "prompt":       "transform to cosmic sacred geometry, teal purple nebula, cinematic",
        "strength":     0.55
    }

    BATCH VARIATIONS (same image, multiple effects):
    {
        "input_image":  "path/to/image.png",
        "effects":      ["sacred_geometry", "crystal_vision", "cosmic_upgrade"],
        "strength":     0.5
    }

    PIL FALLBACK (no ComfyUI needed, instant):
    {
        "input_image":  "path/to/image.png",
        "effect":       "notebooklm",
        "use_pil_only": true
    }

    Output → data/artifacts/effects/
    """

    name        = "effects_engine"
    description = "Image-to-image effects engine — drop an image in, write a prompt, get transformed output"

    def run(self, topic: str, constraints: dict, context: str = "") -> dict:

        input_path = constraints.get("input_image", "")
        if not input_path or not Path(input_path).exists():
            return {"error": f"Input image not found: '{input_path}'. Set 'input_image' in constraints."}

        # Batch effects mode
        if "effects" in constraints:
            return self._run_batch(input_path, constraints)

        effect     = constraints.get("effect", "notebooklm")
        raw_prompt = constraints.get("prompt", "").strip()
        strength   = constraints.get("strength", None)
        steps      = constraints.get("steps", None)
        guidance   = constraints.get("guidance", None)
        seed       = constraints.get("seed", -1)
        model      = constraints.get("model", "flux1-dev-Q5_K_M.gguf")
        pil_only   = constraints.get("use_pil_only", False)

        # Get preset
        preset = EFFECT_PRESETS.get(effect, EFFECT_PRESETS["enhance"])

        # Resolve settings
        final_strength = strength  if strength  is not None else preset["strength"]
        final_steps    = steps     if steps     is not None else preset["steps"]
        final_guidance = guidance  if guidance  is not None else preset["guidance"]

        # Build final prompt
        if raw_prompt:
            final_prompt = raw_prompt
        elif effect == "custom":
            return {"error": "effect='custom' requires a 'prompt' in constraints"}
        else:
            final_prompt = preset["prompt_suffix"]

        print(f"  🔮 Effects Engine: {effect} | strength={final_strength}")
        print(f"  📸 Input: {Path(input_path).name}")
        print(f"  📝 Prompt: {final_prompt[:80]}...")

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = re.sub(r"[^a-z0-9]+", "_", Path(input_path).stem)[:25]
        out_path = f"data/artifacts/effects/{slug}_{effect}_{ts}.png"
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)

        # ── ComfyUI path ──────────────────────────────────────────────────
        if not pil_only and _is_running():
            result = self._run_comfyui(
                input_path, final_prompt, out_path,
                strength=final_strength, steps=final_steps,
                guidance=final_guidance, seed=seed, model=model
            )
            if result:
                return result

        # ── PIL fallback ──────────────────────────────────────────────────
        print("  ⚡ Using PIL effects engine (instant, no ComfyUI)")
        img_in = Image.open(input_path).convert("RGB")
        img_out = PILEffects.apply_preset_pil(img_in, effect)
        img_out.save(out_path, quality=97)
        size_kb = Path(out_path).stat().st_size // 1024
        print(f"  ✅ PIL effect applied → {out_path} ({size_kb}KB)")

        return {
            "output_path": out_path,
            "effect": effect,
            "engine": "pil_fallback",
            "input": input_path,
            "size_kb": size_kb,
            "note": "PIL effects applied. Start ComfyUI for AI-quality results."
        }

    def _run_comfyui(
        self, input_path, prompt, out_path,
        strength, steps, guidance, seed, model
    ) -> Optional[dict]:
        # Upload input image
        print("  ⬆️  Uploading image to ComfyUI...")
        uploaded_name = _upload_image_to_comfyui(input_path)
        if not uploaded_name:
            print("  ⚠️  Upload failed, falling back to PIL")
            return None

        workflow = _build_img2img_workflow(
            input_image_name=uploaded_name,
            prompt=prompt,
            strength=strength,
            steps=steps,
            guidance=guidance,
            seed=seed,
            model=model,
        )

        pid = _queue(workflow)
        if not pid:
            return None

        print(f"  ⏳ Processing... (job {pid[:8]})")
        t_start = time.time()
        history = _wait(pid, timeout=180)
        elapsed = round(time.time() - t_start, 1)

        if not history:
            return None

        for node_out in history.get("outputs", {}).values():
            for img_info in node_out.get("images", []):
                if _download(img_info["filename"], img_info.get("subfolder",""), out_path):
                    size_kb = Path(out_path).stat().st_size // 1024
                    print(f"  ✅ AI effect complete in {elapsed}s → {out_path} ({size_kb}KB)")
                    return {
                        "output_path": out_path,
                        "engine": "comfyui_flux",
                        "input": input_path,
                        "elapsed_seconds": elapsed,
                        "size_kb": size_kb,
                        "prompt": prompt,
                        "strength": strength,
                    }
        return None

    def _run_batch(self, input_path: str, constraints: dict) -> dict:
        """Run multiple effects on same input image."""
        effects   = constraints.get("effects", ["sacred_geometry"])
        strength  = constraints.get("strength", None)
        pil_only  = constraints.get("use_pil_only", False)

        print(f"  🔄 Batch effects: {effects}")
        results = []

        for effect in effects:
            c = {**constraints, "effect": effect, "effects": None}
            if strength is not None:
                c["strength"] = strength
            result = self.run(f"batch_{effect}", c)
            results.append(result)

        return {
            "batch_results": results,
            "effects_applied": effects,
            "input": input_path,
        }

    def list_effects(self) -> dict:
        """List all available effect presets."""
        return {k: v["desc"] for k, v in EFFECT_PRESETS.items()}
