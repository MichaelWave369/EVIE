from __future__ import annotations
from pathlib import Path
import datetime, json, zipfile
from typing import Dict, Any, List, Optional
from app.settings import settings

def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def package_bundle(bundle_name: str, files: List[Path]) -> Path:
    out_dir = Path(settings.data_dir) / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    zip_path = out_dir / f"{bundle_name}__{ts}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            if not f or not f.exists():
                continue
            try:
                # Preserve folder structure inside the ZIP when files live under data_dir
                rel = f.relative_to(Path(settings.data_dir))
                arc = str(rel).replace("\\", "/")
            except Exception:
                arc = f.name
            z.write(f, arcname=arc)
    return zip_path
