from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from app.modules.base import BaseModule
from .base import ModuleResult
from .visual_fx_connectors import VisionFXConnector
from .visual_final_assets import set_preferred_asset


class VisualRanker(BaseModule):
    name = "visual_ranker"

    def _fallback_score(self, image_path: str, *, topic: str, title: str, hook: str) -> tuple[float, list[str]]:
        p = Path(image_path)
        notes: list[str] = []
        score = 50.0
        if p.exists():
            size = p.stat().st_size
            if size > 250_000:
                score += 10
                notes.append("image file size suggests higher detail")
            if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                score += 5
                notes.append("supported image format")
        stem = p.stem.lower()
        topic_tokens = {t for t in re.split(r"[^a-z0-9]+", topic.lower()) if len(t) > 3}
        text_tokens = {t for t in re.split(r"[^a-z0-9]+", f"{title} {hook}".lower()) if len(t) > 3}
        overlap = len(topic_tokens.intersection(stem.split("_"))) + len(text_tokens.intersection(stem.split("_")))
        score += min(20, overlap * 3)
        if not notes:
            notes.append("fallback heuristic ranking")
        return score, notes

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
        input_paths = [str(p) for p in (merged.get("image_paths") or []) if str(p).strip()]
        title = str(merged.get("title") or topic).strip()
        hook = str(merged.get("hook") or "").strip()

        out_dir = Path(merged.get("output_dir") or run_folder) / "visual_ranker"
        out_dir.mkdir(parents=True, exist_ok=True)

        connector = VisionFXConnector()
        ranking_job_type = str(merged.get("ranking_job_type") or "thumbnail_rank")
        final_assets_state_path = str(merged.get("final_assets_state_path") or (out_dir / "visual_final_assets.json"))
        final_asset_category = str(merged.get("final_asset_category") or "final_thumbnail")
        connector_result = connector.rank(
            input_paths,
            topic=topic,
            title=title,
            hook=hook,
            job_type=ranking_job_type,
            final_assets_state_path=final_assets_state_path,
            final_asset_category=final_asset_category,
        )

        ranked: list[dict[str, Any]] = []
        if connector_result.get("status") in {"ok", "done"} and connector_result.get("ranked"):
            ranked = list(connector_result.get("ranked") or [])
            method = "vision_fx"
        else:
            method = "fallback"
            for path in input_paths:
                score, notes = self._fallback_score(path, topic=topic, title=title, hook=hook)
                ranked.append({"path": path, "score": round(score, 2), "notes": notes})
            ranked.sort(key=lambda x: x.get("score", 0), reverse=True)

        best_path = (ranked[0].get("path") if ranked else "")
        preferred_state = set_preferred_asset(final_assets_state_path, category=final_asset_category, asset_path=best_path, source=self.name, note="Auto-selected top ranked image") if best_path else {}
        payload = {
            "topic": topic,
            "status": "ranked" if ranked else "unavailable",
            "ranking_method": method,
            "ranked_images": ranked,
            "best_image_path": best_path,
            "vision_fx": connector_result,
            "preferred_final_asset": ((preferred_state.get("preferred_assets") or {}).get(final_asset_category) or {}).get("asset_path", ""),
            "final_asset_category": final_asset_category,
            "final_asset_state_path": final_assets_state_path,
            "generated_at": datetime.utcnow().isoformat(),
        }
        summary_path = out_dir / f"visual_ranking_{re.sub(r'[^a-z0-9]+', '_', topic.lower())[:40]}_{int(time.time())}.json"
        summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return ModuleResult(name=self.name, artifacts=[str(summary_path)], summary=payload)
