from __future__ import annotations

import base64
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from app.modules.base import BaseModule
from .base import ModuleResult


class ImageGeneratorV2(BaseModule):
    name = "image_generator_v2"

    def _prompt_variations(self, *, topic: str, style: str, hooks: list[str], product_name: str, num_images: int) -> list[str]:
        style_map = {
            "cinematic": "cinematic YouTube thumbnail, bold composition, high contrast, dramatic lighting",
            "product": "premium product visual, studio lighting, clean composition",
            "social": "social media visual, eye-catching, vivid contrast",
            "minimal": "minimalist composition, clean negative space, modern design",
            "cosmic": "cosmic atmosphere, deep gradients, glowing accents",
        }
        base = style_map.get(style, style_map["cinematic"])
        hook_line = hooks[0] if hooks else f"{topic} transformation"
        prompts = []
        for i in range(max(1, min(num_images, 8))):
            prompts.append(
                f"{base}, {topic}, {product_name}, hook: {hook_line}, variation {i+1}, ultra detailed, 4k, no watermark"
            )
        return prompts

    def _generate_via_openai(self, *, prompt: str, out_path: Path) -> bool:
        api_key = os.getenv("EV_OPENAI_API_KEY", "")
        if not api_key:
            return False
        model = os.getenv("EV_OPENAI_IMAGE_MODEL", "gpt-image-1")
        try:
            resp = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "prompt": prompt, "size": "1024x1024"},
                timeout=90,
            )
            if resp.status_code not in (200, 201):
                return False
            body = resp.json()
            item = ((body.get("data") or [{}])[0])
            b64 = item.get("b64_json")
            if b64:
                out_path.write_bytes(base64.b64decode(b64))
                return True
            url = item.get("url")
            if url:
                img = requests.get(url, timeout=30)
                if img.status_code == 200:
                    out_path.write_bytes(img.content)
                    return True
        except Exception:
            return False
        return False

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
        merged = dict(constraints or {})
        style = str(merged.get("style") or merged.get("image_style") or "cinematic").strip().lower()
        num_images = int(merged.get("num_images") or 3)

        wf_meta = merged.get("workflow_step_metadata") or {}
        hooks = (wf_meta.get("hooks_generator") or {}).get("hooks") or []
        product_name = (wf_meta.get("product_packager") or {}).get("product_name") or f"{topic} Pack"

        custom_prompts = merged.get("custom_prompts")
        if isinstance(custom_prompts, list) and custom_prompts:
            prompts = [str(x) for x in custom_prompts[: max(1, min(num_images, 8))]]
        else:
            prompts = self._prompt_variations(
                topic=topic,
                style=style,
                hooks=hooks,
                product_name=product_name,
                num_images=num_images,
            )

        out_dir = Path(merged.get("output_dir") or run_folder) / "images"
        out_dir.mkdir(parents=True, exist_ok=True)

        image_paths: list[str] = []
        variations: list[dict[str, Any]] = []
        mode = "none"

        # Try ComfyUI connector first
        comfy_available = False
        try:
            from app.modules_v2.comfyui_connector import is_comfyui_running, generate_background

            comfy_available = bool(is_comfyui_running())
            if comfy_available:
                mode = "comfyui"
                for i, p in enumerate(prompts, start=1):
                    path = out_dir / f"img_{i:02d}.png"
                    saved = generate_background(prompt=p, save_path=str(path), width=1280, height=720, steps=20, guidance=3.5)
                    ok_path = str(path if saved else "")
                    if ok_path and Path(ok_path).exists():
                        image_paths.append(ok_path)
                        variations.append({"index": i, "prompt": p, "mode": mode, "path": ok_path})
        except Exception:
            comfy_available = False

        # API fallback if ComfyUI unavailable or produced no images
        if not image_paths and bool(merged.get("use_api_fallback", True)):
            mode = "api_fallback"
            for i, p in enumerate(prompts, start=1):
                path = out_dir / f"img_{i:02d}.png"
                if self._generate_via_openai(prompt=p, out_path=path):
                    image_paths.append(str(path))
                    variations.append({"index": i, "prompt": p, "mode": mode, "path": str(path)})

        status = "generated" if image_paths else ("unavailable" if not comfy_available else "failed")
        payload = {
            "topic": topic,
            "style": style,
            "status": status,
            "image_paths": image_paths,
            "prompts_used": prompts,
            "variations": variations,
            "generated_at": datetime.utcnow().isoformat(),
            "mode": mode,
        }

        summary_path = out_dir / f"image_generation_{re.sub(r'[^a-z0-9]+', '_', topic.lower())[:40]}_{int(time.time())}.json"
        summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        artifacts = [str(summary_path), *image_paths]
        return ModuleResult(name=self.name, artifacts=artifacts, summary=payload)
