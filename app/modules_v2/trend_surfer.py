from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from app.modules.base import BaseModule
from .base import ModuleResult
from .prediction_tracker import PredictionTracker


class TrendSurfer(BaseModule):
    name = "trend_surfer"

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
        out_dir = Path(merged.get("output_dir") or run_folder) / "trend_surfer"
        out_dir.mkdir(parents=True, exist_ok=True)

        keywords = merged.get("keywords") or [topic]
        if isinstance(keywords, str):
            keywords = [keywords]

        trend_signals = []
        prediction_candidates = []
        for i, kw in enumerate([str(k) for k in keywords[:8]], start=1):
            momentum = round(0.55 + (i * 0.04), 2)
            trend_signals.append(
                {
                    "keyword": kw,
                    "signal": "rising_interest",
                    "confidence": min(momentum, 0.92),
                    "note": f"Prompt-derived signal for {kw}; validate with channel analytics.",
                }
            )
            prediction_candidates.append(
                {
                    "prediction": f"Interest in {kw} will continue rising over the next 30 days",
                    "confidence": min(momentum - 0.02, 0.9),
                    "horizon_days": 30,
                }
            )

        payload: dict[str, Any] = {
            "topic": topic,
            "status": "ok",
            "analysis_mode": "prompt_heuristic_local",
            "trend_signals": trend_signals,
            "prediction_candidates": prediction_candidates,
            "generated_at": datetime.utcnow().isoformat(),
        }

        if bool(merged.get("create_predictions", False)):
            tracker_res = PredictionTracker().generate(
                topic=topic,
                run_folder=str(out_dir),
                sku=sku,
                tier=tier,
                price_cents=price_cents,
                platforms=platforms,
                constraints={
                    "action": "add",
                    "source": self.name,
                    "prediction_candidates": prediction_candidates,
                    "db_path": merged.get("prediction_db_path", ""),
                },
            )
            payload["prediction_tracker"] = tracker_res.summary

        summary_path = out_dir / f"trend_surfer_{int(time.time())}.json"
        summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return ModuleResult(name=self.name, artifacts=[str(summary_path)], summary=payload)
