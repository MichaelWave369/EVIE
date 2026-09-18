from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Dict, Any, Tuple
import zipfile

from app.settings import settings


@dataclass
class ArtifactCheck:
    ok: bool
    checked: int
    total_bytes: int
    problems: List[str]


def _allowed_exts() -> set[str]:
    exts = set()
    raw = (settings.artifact_allowed_exts or "").strip()
    for part in raw.split(","):
        p = part.strip()
        if not p:
            continue
        if not p.startswith("."):
            p = "." + p
        exts.add(p.lower())
    return exts or {".md", ".txt", ".json"}


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child_res = child.resolve()
        parent_res = parent.resolve()
        return str(child_res).startswith(str(parent_res))
    except Exception:
        return False


def validate_zip(zip_path: Path, max_bytes: int) -> List[str]:
    """Lightweight zip safety check:
    - prevents zip-slip
    - prevents huge total uncompressed size
    """
    problems: List[str] = []
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            total = 0
            for info in z.infolist():
                name = info.filename
                if name.startswith("/") or ".." in Path(name).parts:
                    problems.append(f"zip entry path is unsafe: {name}")
                total += int(info.file_size or 0)
                if total > max_bytes:
                    problems.append(f"zip total uncompressed size too large (> {max_bytes} bytes)")
                    break
    except zipfile.BadZipFile:
        problems.append("bad zip file")
    except Exception as e:
        problems.append(f"zip check error: {e}")
    return problems


def validate_artifacts(paths: Iterable[str]) -> ArtifactCheck:
    """Validate artifact paths are local, inside data_dir, and within size/type limits."""
    allowed = _allowed_exts()
    max_bytes = int(settings.artifact_max_bytes)

    data_root = Path(settings.data_dir)
    problems: List[str] = []
    checked = 0
    total_bytes = 0

    for p in paths:
        if not p:
            continue
        checked += 1
        try:
            path = Path(p)
            if not path.exists():
                problems.append(f"missing: {p}")
                continue

            # Must stay inside data_dir (local guardrail)
            if not _is_within(path, data_root):
                problems.append(f"outside data_dir: {p}")
                continue

            ext = path.suffix.lower()
            if ext and ext not in allowed:
                problems.append(f"disallowed extension: {p} ({ext})")

            size = int(path.stat().st_size)
            total_bytes += size
            if size > max_bytes:
                problems.append(f"file too large: {p} ({size} bytes)")

            if ext == ".zip":
                problems.extend([f"{p}: {msg}" for msg in validate_zip(path, max_bytes=max_bytes)])

        except Exception as e:
            problems.append(f"error checking {p}: {e}")

    return ArtifactCheck(ok=(len(problems) == 0), checked=checked, total_bytes=total_bytes, problems=problems)
