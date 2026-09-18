from __future__ import annotations

import re
from typing import Any, Dict, List

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
URL_TOKEN_RE = re.compile(r"(api[_-]?key|token|secret|bearer)\s*[:=]\s*([A-Za-z0-9_\-]{8,})", re.IGNORECASE)
LONG_HEX_RE = re.compile(r"\b[a-f0-9]{32,}\b", re.IGNORECASE)


def redact_text(text: str) -> str:
    """Redact common sensitive tokens for shareable exports.

    This is intentionally conservative: it tries to remove things that *look* like keys.
    """
    if not text:
        return ""
    t = str(text)
    t = EMAIL_RE.sub("[redacted-email]", t)

    def _sub(m: re.Match) -> str:
        k = m.group(1)
        return f"{k}=[redacted]"

    t = URL_TOKEN_RE.sub(_sub, t)
    t = LONG_HEX_RE.sub("[redacted-hex]", t)
    return t


def redact_obj(obj: Any) -> Any:
    if obj is None:
        return None
    if isinstance(obj, str):
        return redact_text(obj)
    if isinstance(obj, (int, float, bool)):
        return obj
    if isinstance(obj, list):
        return [redact_obj(x) for x in obj]
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            # don't leak secrets by key name
            if isinstance(k, str) and re.search(r"(api[_-]?key|token|secret|password)", k, re.IGNORECASE):
                out[k] = "[redacted]"
            else:
                out[k] = redact_obj(v)
        return out
    return obj
