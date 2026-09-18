from __future__ import annotations
import os, re, json, hashlib, time
from typing import Any

FIB = [1,2,3,5,8,13,21,34,55,89,144]

def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)

def write_text(path: str, text: str):
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

def write_json(path: str, obj: Any):
    write_text(path, json.dumps(obj, indent=2, ensure_ascii=False))

def slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:64] if s else "untitled"

def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def sha256_text(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()

def three_six_nine_sections(title: str, bullets3: list[str], bullets6: list[str], bullets9: list[str]) -> str:
    out = [f"# {title}", ""]
    out += ["## 3 Pillars"] + [f"- {b}" for b in bullets3] + [""]
    out += ["## 6 Deliverables"] + [f"{i+1}. {b}" for i,b in enumerate(bullets6[:6])] + [""]
    out += ["## 9 Notes"] + [f"{i+1}. {b}" for i,b in enumerate(bullets9[:9])] + [""]
    return "\n".join(out)

def phi_split(total: int) -> tuple[int,int]:
    major = max(1, int(round(total * 0.618)))
    minor = max(1, total - major)
    return major, minor
