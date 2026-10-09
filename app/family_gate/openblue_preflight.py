"""EVIE R9: read-only preflight for the OpenBlue/EVIE file-handoff contract.

Checks a local artifact against an R8B review envelope and a conservative
snapshot of OpenBlueprintStudio's evieBridge.js/model.js validation rules.
No file transport, project mutation, keys, agent calls or recipient approval.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from app.family_gate.contracts import validate_proposal

SCHEMA = "evie.openblue-preflight/1"
ARTIFACT_SCHEMA = "openblueprint.evie-proposal/1"
PROJECT_SCHEMA = "openblueprint.project/1"
MAX_BYTES = 5_000_000
MAX_ELEMENTS = 400
SYMBOLS = {"door", "window", "outlet", "network"}


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object field")
        result[key] = value
    return result


def _number(value: Any, low: float, high: float, name: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name} outside supported numeric range")
    return value


def _text(value: Any, limit: int, name: str, *, nonempty: bool = True) -> str:
    if (not isinstance(value, str) or len(value) > limit or
            (nonempty and not value.strip()) or
            any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise ValueError(f"{name} invalid")
    return value


def inspect_openblue_bytes(artifact: bytes) -> dict:
    """Read-only, intentionally conservative preflight; never claims recipient acceptance."""
    if not isinstance(artifact, bytes) or not 0 < len(artifact) <= MAX_BYTES:
        raise ValueError("OpenBlue proposal must be 1–5,000,000 bytes")
    try:
        obj = json.loads(artifact.decode("utf-8"), object_pairs_hook=_unique_pairs,
                         parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid UTF-8 JSON proposal") from exc
    if not isinstance(obj, dict) or obj.get("schemaVersion") != ARTIFACT_SCHEMA:
        raise ValueError("unsupported OpenBlue artifact envelope")
    source = obj.get("source")
    if not isinstance(source, dict) or source.get("system") != "EVIE":
        raise ValueError("EVIE source declaration missing")
    for field in ("cardId", "runId"):
        _text(source.get(field), 120, "source " + field)
    if source.get("mode") not in ("fixture", "generated"):
        raise ValueError("source mode must be fixture or generated")
    project = obj.get("project")
    if not isinstance(project, dict) or project.get("schemaVersion") != PROJECT_SCHEMA:
        raise ValueError("unsupported OpenBlue project schema")
    meta = project.get("metadata")
    if not isinstance(meta, dict):
        raise ValueError("project metadata missing")
    _text(meta.get("title"), 160, "project title", nonempty=False)
    if meta.get("units") not in ("ft", "m"):
        raise ValueError("project units must be ft or m")
    _number(meta.get("grid"), .01, 100, "grid")
    if "updatedAt" in meta and not isinstance(meta["updatedAt"], str):
        raise ValueError("updatedAt must be text")
    walls, symbols = project.get("walls"), project.get("symbols")
    if not isinstance(walls, list) or not isinstance(symbols, list) or len(walls) + len(symbols) > MAX_ELEMENTS:
        raise ValueError("OpenBlue review has 400-element limit")
    seen: set[str] = set()
    for index, item in enumerate(walls):
        if not isinstance(item, dict):
            raise ValueError("wall must be object")
        identity = _text(item.get("id"), 120, "wall ID", nonempty=False)
        if identity in seen:
            raise ValueError("duplicate geometry ID")
        seen.add(identity)
        numbers = {k: _number(item.get(k), -10000, 10000, f"wall {index} {k}")
                   for k in ("x1", "y1", "x2", "y2")}
        _number(item.get("thickness"), .1, 10, "wall thickness")
        _number(item.get("height"), .5, 100, "wall height")
        if math.hypot(numbers["x1"] - numbers["x2"], numbers["y1"] - numbers["y2"]) < .1:
            raise ValueError("wall segment too short")
    for index, item in enumerate(symbols):
        if not isinstance(item, dict):
            raise ValueError("symbol must be object")
        identity = _text(item.get("id"), 120, "symbol ID", nonempty=False)
        if identity in seen:
            raise ValueError("duplicate geometry ID")
        seen.add(identity)
        if item.get("type") not in SYMBOLS:
            raise ValueError("symbol type unsupported")
        for k in ("x", "y"):
            _number(item.get(k), -10000, 10000, f"symbol {index} {k}")
        _number(item.get("rotation", 0), -36000, 36000, "symbol rotation")
    return {
        "schemaVersion": ARTIFACT_SCHEMA, "projectSchema": PROJECT_SCHEMA,
        "sourceMode": source["mode"], "sourceCardId": source["cardId"],
        "runId": source["runId"], "units": meta["units"],
        "walls": len(walls), "symbols": len(symbols),
    }


def preflight_handoff(review_envelope: dict, artifact: bytes, *, now=None) -> dict:
    """Fail closed on expiry, wrong target, digest or geometry. Never mutate anything."""
    envelope = validate_proposal(review_envelope, now=now)
    if envelope["target"] != "openblue" or envelope["artifactKind"] != ARTIFACT_SCHEMA:
        raise ValueError("not an OpenBlue artifact review envelope")
    if len(artifact) != envelope["artifactBytes"]:
        raise ValueError("handoff byte length differs")
    digest = hashlib.sha256(artifact).hexdigest()
    if digest != envelope["artifactSha256"]:
        raise ValueError("handoff digest mismatch")
    report = inspect_openblue_bytes(artifact)
    return {
        "schemaVersion": SCHEMA,
        "result": "preflight_pass",
        "recipient": "openblue",
        "source": "EVIE",
        "artifactSha256": digest,
        "artifactBytes": len(artifact),
        "envelopeNonce": envelope["nonce"],
        "expiresAt": envelope["expiresAt"],
        "sourceMode": report["sourceMode"],
        "walls": report["walls"],
        "symbols": report["symbols"],
        "units": report["units"],
        "schemaMatch": True,
        "digestMatch": True,
        "recipientAccepted": False,
        "transportEnabled": False,
        "executionAuthorized": False,
        "signedOrAuthenticated": False,
        "note": "Local read-only preflight only. OpenBlue must still import, inspect and approve separately.",
    }


def preflight_files(envelope_path: str | Path, artifact_path: str | Path, *, now=None) -> dict:
    review = Path(envelope_path).expanduser()
    source = Path(artifact_path).expanduser()
    if any(not p.is_file() or p.is_symlink() for p in (review, source)):
        raise ValueError("select two existing regular files, not symlinks")
    if review.stat().st_size > 32_000 or source.stat().st_size > MAX_BYTES:
        raise ValueError("selected file too large")
    envelope = json.loads(review.read_text(encoding="utf-8"),
                          object_pairs_hook=_unique_pairs)
    return preflight_handoff(envelope, source.read_bytes(), now=now)
