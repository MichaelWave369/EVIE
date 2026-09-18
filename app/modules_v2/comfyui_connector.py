"""
EVIE ComfyUI Connector
Full REST API bridge between EVIE and ComfyUI running locally.
ComfyUI must be running at http://127.0.0.1:8188 before EVIE calls this.

Supports:
  - Text-to-image via FLUX.1-dev GGUF or SDXL
  - Image-to-image via FLUX Redux
  - Async job queue with polling
  - Automatic download of finished images
  - Smart prompt generation from EVIE topic + style

Drop into: D:/EVIEv4.0/app/modules_v2/comfyui_connector.py
"""

import json, time, uuid, requests, io, os, re
from pathlib import Path
from typing import Optional

COMFYUI_URL = "http://127.0.0.1:8188"
CLIENT_ID   = str(uuid.uuid4())


# ── FLUX GGUF Workflow Template ───────────────────────────────────────────────
# This is the ComfyUI node graph serialized as JSON.
# ComfyUI's /prompt endpoint accepts exactly this format.

def build_flux_gguf_workflow(
    prompt: str,
    negative: str = "",
    width: int = 1920,
    height: int = 1080,
    steps: int = 20,
    guidance: float = 3.5,
    seed: int = -1,
    model: str = "flux1-dev-Q5_K_M.gguf",
    clip_l: str = "clip_l.safetensors",
    t5xxl: str = "t5xxl_fp8_e4m3fn.safetensors",
    vae: str = "ae.safetensors",
) -> dict:
    """
    Returns a ComfyUI workflow JSON for FLUX GGUF text-to-image.
    Nodes: GGUF Loader → CLIP × 2 → Conditioning → Sampler → VAE Decode → Save
    """
    if seed == -1:
        import random
        seed = random.randint(0, 2**32 - 1)

    return {
        "prompt": {
            # Node 1 — Load FLUX GGUF model
            "1": {
                "class_type": "UNETLoader",
                "inputs": {
                    "unet_name": model,
                    "weight_dtype": "default"
                }
            },
            # Node 2 — Load CLIP-L text encoder
            "2": {
                "class_type": "CLIPLoader",
                "inputs": {
                    "clip_name": clip_l,
                    "type": "flux",
                    "device": "default"
                }
            },
            # Node 3 — Load T5-XXL text encoder
            "3": {
                "class_type": "CLIPLoader",
                "inputs": {
                    "clip_name": t5xxl,
                    "type": "flux",
                    "device": "default"
                }
            },
            # Node 4 — Dual CLIP (combines both text encoders)
            "4": {
                "class_type": "DualCLIPLoader",
                "inputs": {
                    "clip_name1": clip_l,
                    "clip_name2": t5xxl,
                    "type": "flux"
                }
            },
            # Node 5 — Encode positive prompt
            "5": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 0],
                    "text": prompt
                }
            },
            # Node 6 — Empty conditioning (FLUX doesn't use negative prompts)
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 0],
                    "text": negative or ""
                }
            },
            # Node 7 — Empty latent image
            "7": {
                "class_type": "EmptySD3LatentImage",
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": 1
                }
            },
            # Node 8 — Flux Guidance
            "8": {
                "class_type": "FluxGuidance",
                "inputs": {
                    "conditioning": ["5", 0],
                    "guidance": guidance
                }
            },
            # Node 9 — KSampler Advanced (FLUX uses this)
            "9": {
                "class_type": "KSamplerSelect",
                "inputs": {
                    "sampler_name": "euler"
                }
            },
            # Node 10 — Basic Scheduler
            "10": {
                "class_type": "BasicScheduler",
                "inputs": {
                    "model": ["1", 0],
                    "scheduler": "simple",
                    "steps": steps,
                    "denoise": 1.0
                }
            },
            # Node 11 — SamplerCustomAdvanced
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
            # Node 12 — Random Noise
            "12": {
                "class_type": "RandomNoise",
                "inputs": {
                    "noise_seed": seed
                }
            },
            # Node 13 — CFG Guider
            "13": {
                "class_type": "BasicGuider",
                "inputs": {
                    "model": ["1", 0],
                    "conditioning": ["8", 0]
                }
            },
            # Node 14 — Load VAE
            "14": {
                "class_type": "VAELoader",
                "inputs": {
                    "vae_name": vae
                }
            },
            # Node 15 — VAE Decode
            "15": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["11", 0],
                    "vae": ["14", 0]
                }
            },
            # Node 16 — Save Image (ComfyUI saves to its output folder)
            "16": {
                "class_type": "SaveImage",
                "inputs": {
                    "images": ["15", 0],
                    "filename_prefix": "evie_bg"
                }
            }
        },
        "client_id": CLIENT_ID
    }


def build_sdxl_workflow(
    prompt: str,
    negative: str = "text, watermark, blurry, low quality",
    width: int = 1920,
    height: int = 1080,
    steps: int = 25,
    cfg: float = 7.0,
    seed: int = -1,
    model: str = "sd_xl_base_1.0.safetensors",
) -> dict:
    """Fallback SDXL workflow if FLUX models aren't installed yet."""
    if seed == -1:
        import random
        seed = random.randint(0, 2**32 - 1)

    return {
        "prompt": {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": model}
            },
            "2": {
                "class_type": "CLIPTextEncode",
                "inputs": {"clip": ["1", 1], "text": prompt}
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {"clip": ["1", 1], "text": negative}
            },
            "4": {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": width, "height": height, "batch_size": 1}
            },
            "5": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["4", 0],
                    "seed": seed, "steps": steps,
                    "cfg": cfg, "sampler_name": "euler",
                    "scheduler": "karras", "denoise": 1.0
                }
            },
            "6": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["5", 0], "vae": ["1", 2]}
            },
            "7": {
                "class_type": "SaveImage",
                "inputs": {"images": ["6", 0], "filename_prefix": "evie_bg"}
            }
        },
        "client_id": CLIENT_ID
    }


# ── Core API functions ────────────────────────────────────────────────────────

def is_comfyui_running(timeout: int = 3) -> bool:
    """Check if ComfyUI is up and responding."""
    try:
        r = requests.get(f"{COMFYUI_URL}/system_stats", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


def queue_prompt(workflow: dict) -> Optional[str]:
    """Send workflow to ComfyUI queue. Returns prompt_id."""
    try:
        r = requests.post(
            f"{COMFYUI_URL}/prompt",
            json=workflow,
            timeout=10
        )
        if r.status_code == 200:
            return r.json().get("prompt_id")
        else:
            print(f"ComfyUI queue error {r.status_code}: {r.text[:200]}")
            return None
    except Exception as e:
        print(f"ComfyUI connection error: {e}")
        return None


def wait_for_completion(prompt_id: str, timeout: int = 300, poll_interval: float = 0.75) -> Optional[dict]:
    """
    Poll ComfyUI until job is complete or timeout.
    Returns history dict when done, None on timeout.
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=5)
            if r.status_code == 200:
                history = r.json()
                if prompt_id in history:
                    job = history[prompt_id]
                    status = job.get("status", {})
                    if status.get("completed", False):
                        return job
                    # Check for errors
                    messages = status.get("messages", [])
                    for msg_type, msg_data in messages:
                        if msg_type == "execution_error":
                            print(f"ComfyUI error: {msg_data}")
                            return None
        except Exception:
            pass
        time.sleep(poll_interval)

    print(f"ComfyUI timeout after {timeout}s")
    return None


def download_image(filename: str, subfolder: str = "", save_path: Optional[str] = None) -> Optional[bytes]:
    """Download a generated image from ComfyUI output."""
    params = {"filename": filename, "type": "output"}
    if subfolder:
        params["subfolder"] = subfolder
    try:
        r = requests.get(f"{COMFYUI_URL}/view", params=params, timeout=30)
        if r.status_code == 200:
            if save_path:
                Path(save_path).parent.mkdir(parents=True, exist_ok=True)
                Path(save_path).write_bytes(r.content)
            return r.content
        return None
    except Exception as e:
        print(f"Image download error: {e}")
        return None


def extract_output_images(history: dict) -> list:
    """Extract list of output image filenames from job history."""
    images = []
    outputs = history.get("outputs", {})
    for node_id, node_output in outputs.items():
        if "images" in node_output:
            for img in node_output["images"]:
                images.append({
                    "filename": img["filename"],
                    "subfolder": img.get("subfolder", ""),
                    "type": img.get("type", "output")
                })
    return images


# ── Smart prompt builder ──────────────────────────────────────────────────────

STYLE_PROMPTS = {
    "notebooklm": (
        "deep cosmic space background, teal and purple nebula, sacred geometry light patterns, "
        "soft glowing particles, dark navy atmosphere, cinematic depth of field, "
        "professional, no text, no watermark, 8k quality"
    ),
    "wellness": (
        "ethereal nature background, soft golden light rays through forest canopy, "
        "bokeh light particles, sacred geometry overlay, deep teal and warm gold, "
        "serene, premium, no text, 8k"
    ),
    "crystal": (
        "ethereal crystal cave, purple amethyst and clear quartz formations, "
        "teal and violet light rays, sacred geometry, mystical atmosphere, "
        "dark background, glowing crystals, cinematic, no text"
    ),
    "cosmic": (
        "cosmic galaxy nebula, deep space, sacred geometry star patterns, "
        "gold and teal light, phi spiral, dark luxury background, "
        "cinematic atmosphere, no text, 8k"
    ),
    "dark_luxury": (
        "dark luxury studio background, deep charcoal and teal, "
        "soft rim lighting, bokeh, premium product atmosphere, "
        "professional photography, no text, 8k"
    ),
    "podcast": (
        "abstract sound wave visualization, deep navy background, "
        "glowing teal waveform, golden sacred geometry, soft light particles, "
        "professional broadcast aesthetic, no text"
    ),
}

def build_prompt_for_topic(topic: str, style: str = "notebooklm", extra: str = "") -> str:
    """Generate a FLUX background prompt from topic + style."""
    base = STYLE_PROMPTS.get(style, STYLE_PROMPTS["notebooklm"])
    if extra:
        return f"{base}, {extra}"
    return base


# ── Main high-level function ───────────────────────────────────────────────────

def generate_background(
    prompt: str,
    width: int = 1920,
    height: int = 1080,
    steps: int = 20,
    guidance: float = 3.5,
    save_path: Optional[str] = None,
    model_type: str = "flux",  # "flux" or "sdxl"
    flux_model: str = "flux1-dev-Q5_K_M.gguf",
    seed: int = -1,
    timeout: int = 120,
) -> Optional[str]:
    """
    High-level function: generate a background image and return local path.
    
    Used by infographic_generator, presentation_generator, video_generator.
    
    Returns: path to saved PNG, or None if generation failed.
    
    Example:
        path = generate_background(
            "cosmic sacred geometry teal nebula dark",
            width=1920, height=1080,
            save_path="data/artifacts/backgrounds/bg_001.png"
        )
    """
    if not is_comfyui_running():
        print("⚠️  ComfyUI is not running. Start it at D:\\ComfyUI\\run_nvidia_gpu.bat")
        print("    Falling back to programmatic background.")
        return None

    print(f"  🎨 Generating AI background ({width}×{height}, {steps} steps)...")

    if model_type == "flux":
        workflow = build_flux_gguf_workflow(
            prompt=prompt,
            width=width, height=height,
            steps=steps, guidance=guidance,
            seed=seed, model=flux_model
        )
    else:
        workflow = build_sdxl_workflow(
            prompt=prompt,
            width=width, height=height,
            steps=steps, seed=seed
        )

    prompt_id = queue_prompt(workflow)
    if not prompt_id:
        print("  ❌ Failed to queue prompt")
        return None

    print(f"  ⏳ Waiting for ComfyUI (job {prompt_id[:8]}...)...")
    t_start = time.time()

    history = wait_for_completion(prompt_id, timeout=timeout)
    if not history:
        print("  ❌ ComfyUI job timed out or errored")
        return None

    elapsed = time.time() - t_start
    images = extract_output_images(history)
    if not images:
        print("  ❌ No output images found in job history")
        return None

    img_info = images[0]
    if save_path is None:
        slug = re.sub(r"[^a-z0-9]+", "_", prompt[:30].lower())
        save_path = f"data/artifacts/backgrounds/bg_{slug}_{int(time.time())}.png"

    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    img_bytes = download_image(img_info["filename"], img_info["subfolder"], save_path)

    if img_bytes:
        size_kb = len(img_bytes) // 1024
        print(f"  ✅ Background ready in {elapsed:.1f}s — {size_kb}KB → {save_path}")
        return save_path

    return None


# ── EVIE Module wrapper ───────────────────────────────────────────────────────

class ImageGenerator:
    """
    EVIE module for AI image generation via ComfyUI.
    
    Constraint examples:
    {
        "style": "notebooklm",          // or wellness, crystal, cosmic, dark_luxury, podcast
        "width": 1920,
        "height": 1080,
        "steps": 20,                    // 20 for quality, 4 for schnell speed
        "guidance": 3.5,
        "model_type": "flux",           // flux or sdxl
        "flux_model": "flux1-dev-Q5_K_M.gguf",
        "extra_prompt": "crystal chakra energy",
        "seed": -1                      // -1 for random
    }
    """

    name = "image_generator"
    description = "Generate AI background images via local ComfyUI + FLUX"

    def run(self, topic: str, constraints: dict, context: str = "") -> dict:
        style       = constraints.get("style", "notebooklm")
        width       = constraints.get("width", 1920)
        height      = constraints.get("height", 1080)
        steps       = constraints.get("steps", 20)
        guidance    = constraints.get("guidance", 3.5)
        model_type  = constraints.get("model_type", "flux")
        flux_model  = constraints.get("flux_model", "flux1-dev-Q5_K_M.gguf")
        extra       = constraints.get("extra_prompt", "")
        seed        = constraints.get("seed", -1)

        prompt = build_prompt_for_topic(topic, style, extra)
        
        import re, time
        slug = re.sub(r"[^a-z0-9]+", "_", topic.lower())[:30]
        save_path = f"data/artifacts/backgrounds/bg_{slug}_{int(time.time())}.png"

        result_path = generate_background(
            prompt=prompt,
            width=width, height=height,
            steps=steps, guidance=guidance,
            save_path=save_path,
            model_type=model_type,
            flux_model=flux_model,
            seed=seed,
        )

        if result_path:
            return {"artifact_path": result_path, "prompt": prompt, "style": style}
        else:
            return {"error": "ComfyUI not running or generation failed", "prompt": prompt}
