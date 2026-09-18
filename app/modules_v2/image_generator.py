"""
EVIE Image Generator Module
Text-to-image generation via ComfyUI/FLUX running locally.

Two modes:
  1. PROMPT MODE  — you write the full prompt
  2. TOPIC MODE   — EVIE builds the prompt from your topic + style preset

Style presets tuned for The Porch is Eternal brand:
  notebooklm, cosmic, crystal, chakra, wellness, sacred, 
  product, podcast, portrait, abstract, dark_luxury

Output: PNG saved to data/artifacts/images/

Drop into: D:/EVIEv4.0/app/modules_v2/image_generator.py
"""

import os, re, time, json, requests, uuid, random
from pathlib import Path
from datetime import datetime
from typing import Optional
from .base import BaseModule


# ── ComfyUI connection ────────────────────────────────────────────────────────

COMFYUI_URL = "http://127.0.0.1:8188"
CLIENT_ID   = str(uuid.uuid4())


# ── Style Preset Library ─────────────────────────────────────────────────────
# Each preset = (positive_prompt_suffix, negative_prompt, recommended_steps, guidance)

STYLE_PRESETS = {

    "notebooklm": {
        "positive": (
            "deep cosmic nebula background, sacred geometry light patterns, "
            "teal and deep purple atmosphere, soft glowing particles, "
            "cinematic depth of field, dark navy, professional, masterpiece, 8k"
        ),
        "negative": "text, watermark, logo, blurry, low quality, cartoon, anime",
        "steps": 22, "guidance": 3.5, "width": 1920, "height": 1080,
        "desc": "Dark cosmic atmosphere with teal/purple sacred geometry"
    },

    "cosmic": {
        "positive": (
            "cosmic galaxy, spiral nebula, star field, golden phi spiral, "
            "sacred geometry overlay, deep space, teal and gold light, "
            "cinematic, highly detailed, 8k, dark background"
        ),
        "negative": "text, watermark, blurry, low quality, flat, cartoon",
        "steps": 25, "guidance": 3.5, "width": 1920, "height": 1080,
        "desc": "Deep space galaxy with golden sacred geometry"
    },

    "crystal": {
        "positive": (
            "ethereal crystal cave, amethyst and clear quartz formations, "
            "teal violet purple light rays, sacred geometry, mystical atmosphere, "
            "glowing crystals, cinematic lighting, dark background, 8k"
        ),
        "negative": "text, watermark, blurry, low quality, flat lighting",
        "steps": 25, "guidance": 3.8, "width": 1080, "height": 1920,
        "desc": "Mystical crystal cave with violet light rays"
    },

    "chakra": {
        "positive": (
            "chakra energy mandala, rainbow light rays, sacred lotus flower, "
            "kundalini energy rising, golden divine light, ethereal spiritual, "
            "highly detailed mandala, dark background, 8k"
        ),
        "negative": "text, watermark, blurry, low quality, cartoonish",
        "steps": 28, "guidance": 4.0, "width": 1080, "height": 1080,
        "desc": "Chakra energy mandala with rainbow divine light"
    },

    "wellness": {
        "positive": (
            "ethereal forest light, golden hour sunbeams through trees, "
            "bokeh light particles, sacred geometry overlay, nature sanctuary, "
            "warm gold and green, serene, cinematic, 8k"
        ),
        "negative": "text, watermark, blurry, low quality, urban, people",
        "steps": 22, "guidance": 3.5, "width": 1080, "height": 1920,
        "desc": "Golden forest sanctuary with bokeh light"
    },

    "sacred": {
        "positive": (
            "ancient sacred temple, golden divine light shafts, "
            "stone pillars, sacred geometry inscriptions, mystical fog, "
            "epic cinematic, god rays, highly detailed, 8k"
        ),
        "negative": "text, watermark, blurry, low quality, modern, cartoon",
        "steps": 28, "guidance": 3.8, "width": 1920, "height": 1080,
        "desc": "Ancient sacred temple with divine light shafts"
    },

    "product": {
        "positive": (
            "luxury product photography background, dark studio, "
            "soft teal rim lighting, bokeh, premium minimalist, "
            "professional photography, no objects, dark charcoal background"
        ),
        "negative": "text, watermark, products, objects, blurry, low quality",
        "steps": 20, "guidance": 3.0, "width": 1920, "height": 1080,
        "desc": "Dark luxury studio background for product shots"
    },

    "podcast": {
        "positive": (
            "abstract sound wave visualization, deep navy background, "
            "glowing teal audio waveform, golden sacred geometry, "
            "soft bokeh light particles, broadcast aesthetic, cinematic"
        ),
        "negative": "text, watermark, blurry, low quality, people, faces",
        "steps": 22, "guidance": 3.5, "width": 1920, "height": 1080,
        "desc": "Abstract audio visualization for podcast artwork"
    },

    "portrait_bg": {
        "positive": (
            "cinematic portrait background, soft bokeh, teal and purple "
            "gradient, sacred geometry light overlay, dark moody atmosphere, "
            "studio quality, shallow depth of field, 8k"
        ),
        "negative": "text, watermark, faces, people, blurry foreground",
        "steps": 22, "guidance": 3.5, "width": 1080, "height": 1350,
        "desc": "Cinematic portrait background with bokeh"
    },

    "abstract": {
        "positive": (
            "abstract generative art, fluid simulation, teal gold purple, "
            "sacred geometry flow, mathematical beauty, "
            "dark background, highly detailed, 8k, masterpiece"
        ),
        "negative": "text, watermark, blurry, low quality, realistic photo",
        "steps": 28, "guidance": 4.0, "width": 1080, "height": 1080,
        "desc": "Abstract generative sacred geometry art"
    },

    "dark_luxury": {
        "positive": (
            "dark luxury background, obsidian black surface, gold foil texture, "
            "subtle sacred geometry, premium minimalist, "
            "depth and dimension, 8k"
        ),
        "negative": "text, watermark, blurry, low quality, bright, colorful",
        "steps": 20, "guidance": 3.2, "width": 1920, "height": 1080,
        "desc": "Dark obsidian with gold luxury texture"
    },

    "phi369": {
        "positive": (
            "369 sacred mathematics, phi ratio spiral, tesla 369 vortex, "
            "sacred geometry golden ratio, fibonacci sequence visualization, "
            "dark background, teal gold light, mathematical universe, 8k"
        ),
        "negative": "text, watermark, blurry, low quality, cartoon",
        "steps": 28, "guidance": 4.0, "width": 1080, "height": 1080,
        "desc": "PHI369 sacred mathematics visualization"
    },

    "sovereignty": {
        "positive": (
            "sovereign energy, crown of light, golden divine authority, "
            "sacred geometry throne room, epic fantasy realism, "
            "dark dramatic lighting, teal and gold, cinematic, 8k"
        ),
        "negative": "text, watermark, blurry, low quality, cartoonish",
        "steps": 28, "guidance": 4.0, "width": 1080, "height": 1920,
        "desc": "Sovereign divine energy with crown of light"
    },
}


# ── FLUX GGUF Workflow ────────────────────────────────────────────────────────

def _build_workflow(
    prompt: str,
    negative: str = "",
    width: int = 1920,
    height: int = 1080,
    steps: int = 22,
    guidance: float = 3.5,
    seed: int = -1,
    model: str = "flux1-dev-Q5_K_M.gguf",
    clip_l: str = "clip_l.safetensors",
    t5xxl: str = "t5xxl_fp8_e4m3fn.safetensors",
    vae: str = "ae.safetensors",
) -> dict:
    if seed == -1:
        seed = random.randint(0, 2**32 - 1)

    return {
        "prompt": {
            "4": {
                "class_type": "DualCLIPLoader",
                "inputs": {
                    "clip_name1": clip_l,
                    "clip_name2": t5xxl,
                    "type": "flux"
                }
            },
            "5": {
                "class_type": "CLIPTextEncode",
                "inputs": {"clip": ["4", 0], "text": prompt}
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {"clip": ["4", 0], "text": negative}
            },
            "7": {
                "class_type": "EmptySD3LatentImage",
                "inputs": {"width": width, "height": height, "batch_size": 1}
            },
            "8": {
                "class_type": "FluxGuidance",
                "inputs": {"conditioning": ["5", 0], "guidance": guidance}
            },
            "9": {
                "class_type": "KSamplerSelect",
                "inputs": {"sampler_name": "euler"}
            },
            "10": {
                "class_type": "BasicScheduler",
                "inputs": {
                    "model": ["1", 0],
                    "scheduler": "simple",
                    "steps": steps,
                    "denoise": 1.0
                }
            },
            "11": {
                "class_type": "SamplerCustomAdvanced",
                "inputs": {
                    "noise": ["12", 0],
                    "guider": ["13", 0],
                    "sampler": ["9", 0],
                    "sigmas": ["10", 0],
                    "latent_image": ["7", 0]
                }
            },
            "12": {
                "class_type": "RandomNoise",
                "inputs": {"noise_seed": seed}
            },
            "13": {
                "class_type": "BasicGuider",
                "inputs": {
                    "model": ["1", 0],
                    "conditioning": ["8", 0]
                }
            },
            "14": {
                "class_type": "VAELoader",
                "inputs": {"vae_name": vae}
            },
            "15": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["11", 0], "vae": ["14", 0]}
            },
            "16": {
                "class_type": "SaveImage",
                "inputs": {
                    "images": ["15", 0],
                    "filename_prefix": "evie_gen"
                }
            },
            "1": {
                "class_type": "UNETLoader",
                "inputs": {"unet_name": model, "weight_dtype": "default"}
            },
        },
        "client_id": CLIENT_ID
    }


# ── ComfyUI API helpers ───────────────────────────────────────────────────────

def _is_running() -> bool:
    try:
        return requests.get(f"{COMFYUI_URL}/system_stats", timeout=3).status_code == 200
    except:
        return False

def _queue(workflow: dict) -> Optional[str]:
    try:
        r = requests.post(f"{COMFYUI_URL}/prompt", json=workflow, timeout=10)
        if r.status_code == 200:
            return r.json().get("prompt_id")
    except Exception as e:
        print(f"  Queue error: {e}")
    return None

def _wait(prompt_id: str, timeout: int = 180) -> Optional[dict]:
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=5)
            if r.status_code == 200:
                h = r.json()
                if prompt_id in h and h[prompt_id].get("status", {}).get("completed"):
                    return h[prompt_id]
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


# ── LLM prompt builder ────────────────────────────────────────────────────────

PROMPT_SYSTEM = """You are an expert AI image prompt engineer specializing in FLUX.1 text-to-image generation.
Given a topic and style, write a precise, evocative FLUX prompt (60-120 words).
Focus on: visual elements, lighting, atmosphere, color palette, technical quality.
Always end with: masterpiece, highly detailed, professional
Never include: people (unless requested), text, watermarks, logos.
Respond with ONLY the prompt. No explanation."""

def _build_llm_prompt(topic: str, style: str, extra: str = "") -> str:
    """Use Claude Haiku or GPT to build a refined image prompt."""
    style_context = STYLE_PRESETS.get(style, {}).get("desc", style)
    user_msg = f"Topic: {topic}\nStyle: {style_context}\nExtra requirements: {extra or 'none'}\n\nWrite the FLUX image prompt:"

    try:
        from app.settings import settings
        if settings.llm_backend == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=200,
                system=PROMPT_SYSTEM,
                messages=[{"role": "user", "content": user_msg}]
            )
            return msg.content[0].text.strip()
        elif settings.llm_backend == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=settings.openai_api_key)
            r = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": PROMPT_SYSTEM},
                    {"role": "user", "content": user_msg}
                ],
                max_tokens=200
            )
            return r.choices[0].message.content.strip()
    except Exception:
        pass

    # Fallback — combine topic with style preset
    base = STYLE_PRESETS.get(style, STYLE_PRESETS["notebooklm"])["positive"]
    return f"{topic}, {base}"


# ── Main Module ───────────────────────────────────────────────────────────────

class ImageGenerator(BaseModule):
    """
    EVIE text-to-image generator via ComfyUI + FLUX.1-dev.

    Two modes:
      PROMPT MODE  — set "prompt" in constraints to use directly
      TOPIC MODE   — set "style" and let EVIE build the prompt via LLM

    Constraint examples:
    {
        "style":      "crystal",
        "prompt":     "",                         // leave blank for auto
        "extra":      "with selenite and amethyst",
        "width":      1080,
        "height":     1920,
        "steps":      25,
        "guidance":   3.5,
        "seed":       -1,
        "model":      "flux1-dev-Q5_K_M.gguf",
        "batch":      1,
        "save_name":  "my_crystal_bg"
    }

    Batch example (generates multiple variations):
    {
        "style": "cosmic",
        "batch": 4,
        "steps": 20
    }

    All outputs → data/artifacts/images/
    """

    name        = "image_generator"
    description = "Text-to-image generation via local ComfyUI + FLUX.1-dev"

    def run(self, topic: str, constraints: dict, context: str = "") -> dict:

        if not _is_running():
            return {
                "error": (
                    "ComfyUI is not running. "
                    "Start it: D:\\ComfyUI\\run_nvidia_gpu.bat → then retry."
                ),
                "hint": "See RTX5070_ComfyUI_Setup_Guide.md for installation steps"
            }

        style      = constraints.get("style", "notebooklm")
        raw_prompt = constraints.get("prompt", "").strip()
        extra      = constraints.get("extra", "")
        steps      = constraints.get("steps", None)
        guidance   = constraints.get("guidance", None)
        width      = constraints.get("width", None)
        height     = constraints.get("height", None)
        seed       = constraints.get("seed", -1)
        model      = constraints.get("model", "flux1-dev-Q5_K_M.gguf")
        batch      = constraints.get("batch", 1)
        save_name  = constraints.get("save_name", "")

        preset = STYLE_PRESETS.get(style, STYLE_PRESETS["notebooklm"])

        # Resolve final settings (constraints override presets)
        final_steps    = steps    or preset["steps"]
        final_guidance = guidance or preset["guidance"]
        final_width    = width    or preset["width"]
        final_height   = height   or preset["height"]
        final_negative = preset["negative"]

        # Build or use prompt
        if raw_prompt:
            final_prompt = raw_prompt
            prompt_source = "manual"
        else:
            print(f"  ✍️  Building prompt via LLM for topic: '{topic}' / style: '{style}'")
            final_prompt = _build_llm_prompt(topic, style, extra)
            prompt_source = "llm"

        print(f"  🎨 Image Generator: {style} | {final_width}×{final_height} | {final_steps} steps")
        print(f"  📝 Prompt: {final_prompt[:80]}...")

        outputs = []
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        for i in range(batch):
            if batch > 1:
                print(f"  🔄 Batch {i+1}/{batch}...")
            
            current_seed = seed if seed != -1 else -1

            workflow = _build_workflow(
                prompt    = final_prompt,
                negative  = final_negative,
                width     = final_width,
                height    = final_height,
                steps     = final_steps,
                guidance  = final_guidance,
                seed      = current_seed,
                model     = model,
            )

            prompt_id = _queue(workflow)
            if not prompt_id:
                outputs.append({"error": f"Failed to queue batch {i+1}"})
                continue

            t_start = time.time()
            history = _wait(prompt_id, timeout=180)
            elapsed = round(time.time() - t_start, 1)

            if not history:
                outputs.append({"error": f"Timeout on batch {i+1}"})
                continue

            # Extract images
            for node_out in history.get("outputs", {}).values():
                for img_info in node_out.get("images", []):
                    fname = img_info["filename"]
                    subfolder = img_info.get("subfolder", "")
                    
                    slug = save_name or re.sub(r"[^a-z0-9]+", "_", topic.lower())[:30]
                    out_path = f"data/artifacts/images/{slug}_{style}_{ts}_{i+1:02d}.png"

                    if _download(fname, subfolder, out_path):
                        size_kb = Path(out_path).stat().st_size // 1024
                        print(f"  ✅ Image {i+1} ready in {elapsed}s — {size_kb}KB → {out_path}")
                        outputs.append({
                            "path": out_path,
                            "elapsed_seconds": elapsed,
                            "size_kb": size_kb,
                            "seed": current_seed,
                            "style": style,
                        })

        # Write prompt log
        log_path = f"data/artifacts/images/{ts}_prompt_log.json"
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        Path(log_path).write_text(json.dumps({
            "topic": topic,
            "style": style,
            "prompt": final_prompt,
            "prompt_source": prompt_source,
            "settings": {
                "width": final_width, "height": final_height,
                "steps": final_steps, "guidance": final_guidance,
                "model": model, "batch": batch
            },
            "outputs": outputs,
            "generated": datetime.now().isoformat(),
        }, indent=2))

        return {
            "outputs": outputs,
            "prompt": final_prompt,
            "style": style,
            "batch_count": len(outputs),
            "prompt_log": log_path,
        }


    def list_styles(self) -> dict:
        """Return all available style presets with descriptions."""
        return {k: v["desc"] for k, v in STYLE_PRESETS.items()}
