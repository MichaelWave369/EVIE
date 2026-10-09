import json
import math
import hashlib
import pytest
from pathlib import Path
from app.modules import REGISTRY
from app.modules.openblueprint_floor_plan import OpenBlueprintFloorPlanModule, build_project

def test_module_is_registered():
    assert "openblueprint_floor_plan" in REGISTRY

def test_geometry_roundtrip_shape():
    project = build_project("My office", {"width": 24, "depth": 12, "partition": "vertical"})
    assert project["schemaVersion"] == "openblueprint.project/1"
    assert len(project["walls"]) == 5
    assert len(project["symbols"]) == 2
    assert len({a["id"] for a in project["walls"] + project["symbols"]}) == 7

def test_metric_defaults():
    project = build_project("Metric room", {"units": "m", "include_door": False, "include_network": False})
    assert project["walls"][0]["x2"] == 8
    assert project["walls"][0]["height"] == 2.7
    assert project["symbols"] == []

@pytest.mark.parametrize("bad", [
    {"width": 1}, {"width": float("nan")}, {"width": float("inf")},
    {"units": "inch"}, {"wall_thickness": 10, "width": 3},
    {"partition": "diagonal"}, {"partition_ratio": 0},
    {"include_network": "true"}, {"shell": "echo NO"},
])
def test_rejects_bad_constraints(bad):
    with pytest.raises(ValueError):
        build_project("Concept", bad)

def test_produces_receipt_and_unique_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(OpenBlueprintFloorPlanModule, "artifact_root",
        lambda self, slug, ns: tmp_path / ns / slug)
    module = OpenBlueprintFloorPlanModule()
    out = module.generate("Concept", {})
    artifact = Path(out.artifact_paths[0])
    receipt = json.loads(Path(out.artifact_paths[1]).read_text(encoding="utf-8"))
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    assert payload["schemaVersion"] == "openblueprint.evie-proposal/1"
    assert payload["source"]["mode"] == "generated"
    assert receipt["sha256"] == hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert module.generate("Concept", {}).artifact_paths != out.artifact_paths
