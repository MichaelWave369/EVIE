from __future__ import annotations

from pathlib import Path

from app.settings import settings

# Compatibility shim for v2.x modules that expect EV_DB_PATH etc.
EV_DATA_DIR = Path(settings.data_dir)
EV_DB_PATH = EV_DATA_DIR / "db.sqlite"
EV_ARTIFACTS_DIR = EV_DATA_DIR / "artifacts"
EV_RUNS_DIR = EV_DATA_DIR / "runs"
