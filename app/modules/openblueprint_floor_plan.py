"""Deterministic local CAD proposal producer for OpenBlueprint Studio."""
import hashlib
import json
import math
import uuid
from datetime import datetime, timezone
from app.modules.base import BaseModule, ModuleResult
from app.flywheel.slug import slugify

CARD_ID = "openblueprint_floor_plan"

def bounded(value, key, lo, hi):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lo <= value <= hi:
        raise ValueError(key + " must be finite and in range")
    return round(float(value), 6)

def build_project(topic, constraints):
    if not isinstance(topic, str) or not topic.strip() or len(topic) > 160:
        raise ValueError("topic must be 1-160 characters")
    if not isinstance(constraints, dict):
        raise ValueError("constraints must be a JSON object")
    allowed = {"units", "width", "depth", "wall_height", "wall_thickness", "grid", "partition", "partition_ratio", "include_door", "include_network"}
    if set(constraints) - allowed:
        raise ValueError("unsupported constraints")
    units = constraints.get("units", "ft")
    if units not in ("ft", "m"):
        raise ValueError("units must be ft or m")
    metric = units == "m"
    width = bounded(constraints.get("width", 8 if metric else 28), "width", 2, 200)
    depth = bounded(constraints.get("depth", 6 if metric else 20), "depth", 2, 200)
    height = bounded(constraints.get("wall_height", 2.7 if metric else 9), "height", .5, 100)
    thickness = bounded(constraints.get("wall_thickness", .15 if metric else .5), "thickness", .1, 10)
    grid = bounded(constraints.get("grid", .25 if metric else 1), "grid", .01, 100)
    ratio = bounded(constraints.get("partition_ratio", .5), "ratio", .2, .8)
    partition = constraints.get("partition", "none")
    if partition not in ("none", "vertical", "horizontal"):
        raise ValueError("unsupported partition")
    if thickness * 2 >= min(width, depth):
        raise ValueError("walls too thick for room")
    for key in ("include_door", "include_network"):
        if not isinstance(constraints.get(key, True), bool):
            raise ValueError(key + " must be boolean")
    def wall(name, x1, y1, x2, y2):
        return {"id": name, "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "height": height, "thickness": thickness}
    walls = [wall("evie-n", 0, 0, width, 0), wall("evie-e", width, 0, width, depth),
             wall("evie-s", width, depth, 0, depth), wall("evie-w", 0, depth, 0, 0)]
    if partition == "vertical":
        x = round(width * ratio, 6)
        walls.append(wall("evie-p", x, 0, x, depth))
    elif partition == "horizontal":
        y = round(depth * ratio, 6)
        walls.append(wall("evie-p", 0, y, width, y))
    symbols = []
    if constraints.get("include_door", True):
        symbols.append({"id": "evie-door", "type": "door", "x": round(width / 2, 6), "y": depth, "rotation": 0})
    if constraints.get("include_network", True):
        symbols.append({"id": "evie-net", "type": "network", "x": round(width * .75, 6),
                        "y": round(depth * .75, 6), "rotation": 0})
    return {"schemaVersion": "openblueprint.project/1",
            "metadata": {"title": topic.strip(), "units": units, "grid": grid,
                         "updatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")},
            "walls": walls, "symbols": symbols}

class OpenBlueprintFloorPlanModule(BaseModule):
    name = CARD_ID
    def generate(self, topic, constraints):
        project = build_project(topic, constraints)
        run_id = "evie-cad-" + uuid.uuid4().hex
        envelope = {"schemaVersion": "openblueprint.evie-proposal/1",
                    "source": {"system": "EVIE", "cardId": CARD_ID, "runId": run_id, "mode": "generated"},
                    "project": project}
        data = (json.dumps(envelope, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        folder = self.artifact_root(slugify(topic), CARD_ID) / run_id
        folder.mkdir(parents=True, exist_ok=False)
        proposal = folder / "openblueprint.evie-proposal.json"
        receipt = folder / "sha256-receipt.json"
        digest = hashlib.sha256(data).hexdigest()
        proposal.write_bytes(data)
        receipt.write_text(json.dumps({"runId": run_id, "sha256": digest,
                  "note": "File integrity digest, not authenticated provenance"}, indent=2) + "\n", encoding="utf-8")
        return ModuleResult(artifact_paths=[str(proposal), str(receipt)],
                 metadata={"schemaVersion": "openblueprint.evie-proposal/1",
                           "human_approval_required": True, "sha256": digest})
