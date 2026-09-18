from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from app.modules.base import BaseModule
from .base import ModuleResult


class PredictionTracker(BaseModule):
    name = "prediction_tracker"

    def _db_path(self, merged: dict[str, Any], run_folder: str) -> Path:
        if merged.get("db_path"):
            return Path(str(merged.get("db_path")))
        base = Path(merged.get("output_dir") or run_folder)
        return base / "prediction_tracker" / "prediction_tracker.db"

    def _ensure_schema(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    prediction TEXT NOT NULL,
                    confidence REAL DEFAULT 0.0,
                    horizon_days INTEGER DEFAULT 30,
                    status TEXT DEFAULT 'open',
                    outcome TEXT DEFAULT '',
                    source TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

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
        action = str(merged.get("action") or "add").strip().lower()
        db_path = self._db_path(merged, run_folder)
        self._ensure_schema(db_path)

        out_dir = Path(merged.get("output_dir") or run_folder) / "prediction_tracker"
        out_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.utcnow().isoformat()

        payload: dict[str, Any] = {"topic": topic, "action": action, "db_path": str(db_path), "status": "ok"}
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            if action == "update":
                prediction_id = int(merged.get("prediction_id") or 0)
                if prediction_id <= 0:
                    raise ValueError("prediction_id is required for update action")
                new_status = str(merged.get("status") or "resolved")
                outcome = str(merged.get("outcome") or "")
                conn.execute(
                    "UPDATE predictions SET status=?, outcome=?, updated_at=? WHERE id=?",
                    (new_status, outcome, now, prediction_id),
                )
                conn.commit()
                row = conn.execute("SELECT * FROM predictions WHERE id=?", (prediction_id,)).fetchone()
                payload["updated"] = dict(row) if row else {}
            elif action == "list":
                limit = max(1, min(100, int(merged.get("limit") or 20)))
                rows = conn.execute("SELECT * FROM predictions ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
                payload["predictions"] = [dict(r) for r in rows]
            else:
                prediction_text = str(merged.get("prediction_text") or merged.get("prediction") or f"{topic} demand will increase")
                confidence = float(merged.get("confidence") or 0.62)
                horizon_days = int(merged.get("horizon_days") or 30)
                source = str(merged.get("source") or self.name)
                conn.execute(
                    """
                    INSERT INTO predictions (topic, prediction, confidence, horizon_days, status, outcome, source, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 'open', '', ?, ?, ?)
                    """,
                    (topic, prediction_text, confidence, horizon_days, source, now, now),
                )
                # optional bulk candidates from trend_surfer
                candidates = merged.get("prediction_candidates") or []
                if not candidates:
                    wf_meta = merged.get("workflow_step_metadata") or {}
                    trend_meta = wf_meta.get("trend_surfer") or {}
                    if isinstance(trend_meta, dict):
                        trend_sum = trend_meta.get("v2_summary") if isinstance(trend_meta.get("v2_summary"), dict) else trend_meta
                        candidates = trend_sum.get("prediction_candidates") or []
                if isinstance(candidates, list):
                    for c in candidates[:10]:
                        text = str((c or {}).get("prediction") or "").strip()
                        if not text:
                            continue
                        conf = float((c or {}).get("confidence") or 0.55)
                        hz = int((c or {}).get("horizon_days") or 30)
                        conn.execute(
                            """
                            INSERT INTO predictions (topic, prediction, confidence, horizon_days, status, outcome, source, created_at, updated_at)
                            VALUES (?, ?, ?, ?, 'open', '', ?, ?, ?)
                            """,
                            (topic, text, conf, hz, source, now, now),
                        )
                conn.commit()
                rows = conn.execute("SELECT * FROM predictions WHERE topic=? ORDER BY id DESC LIMIT 20", (topic,)).fetchall()
                payload["predictions"] = [dict(r) for r in rows]
        except Exception as e:
            payload["status"] = "error"
            payload["error"] = str(e)
        finally:
            conn.close()

        summary_path = out_dir / f"prediction_tracker_{int(time.time())}.json"
        summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return ModuleResult(name=self.name, artifacts=[str(summary_path), str(db_path)], summary=payload)
