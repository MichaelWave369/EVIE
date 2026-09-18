from __future__ import annotations

import json
import os
import sys
import py_compile
from pathlib import Path
from typing import Any, Dict, List

SUSPICIOUS_PATTERNS = [
    "os.system(",
    "subprocess.",
    "socket.",
    "requests.",
    "urllib.",
    "http://",
    "https://",
]


def _collect_py(paths: List[str]) -> List[Path]:
    out: List[Path] = []
    for p in paths:
        try:
            pp = Path(p)
            if pp.is_dir():
                out.extend(list(pp.rglob("*.py")))
            elif pp.is_file() and pp.suffix.lower() == ".py":
                out.append(pp)
        except Exception:
            continue
    # de-dup
    uniq = []
    seen = set()
    for p in out:
        rp = str(p.resolve())
        if rp not in seen:
            uniq.append(p)
            seen.add(rp)
    return uniq


def main() -> None:
    payload = json.loads(sys.stdin.read() or "{}")
    paths = payload.get("paths") or []
    if not isinstance(paths, list):
        paths = []

    files = _collect_py([str(x) for x in paths])

    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    compiled = 0

    for f in files:
        try:
            txt = f.read_text(encoding="utf-8", errors="ignore")
            for pat in SUSPICIOUS_PATTERNS:
                if pat in txt:
                    warnings.append({"file": str(f), "warning": f"pattern: {pat}"})
                    break
        except Exception:
            pass

        try:
            py_compile.compile(str(f), doraise=True)
            compiled += 1
        except Exception as e:
            errors.append({"file": str(f), "error": str(e)})

    out = {
        "ok": len(errors) == 0,
        "python_files": len(files),
        "compiled": compiled,
        "errors": errors,
        "warnings": warnings,
        "sandbox_dir": os.environ.get("EVIE_SANDBOX_DIR"),
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
