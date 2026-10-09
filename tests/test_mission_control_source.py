"""Source registry ↔ public Mission Control facts and no runtimes."""
import json
import re
from pathlib import Path
from app.modules import REGISTRY

ROOT = Path(__file__).resolve().parents[1]

def test_source_registry_is_suitable_for_static_public_snapshot():
    registry = (ROOT / "app" / "modules" / "__init__.py").read_text(encoding="utf-8")
    body = registry.split("\nREGISTRY = {", 1)[1].split("\n}", 1)[0]
    names = re.findall(r'^\s*"([a-z0-9_]+)"\s*:\s*([A-Za-z_]\w*)\(\s*\),\s*$', body, re.M)
    assert len(names) == len(REGISTRY) >= 100
    assert {key for key, _klass in names} == set(REGISTRY)

def test_workflow_snapshot_has_valid_direct_dependencies():
    flows = json.loads((ROOT / "configs" / "workflows.json").read_text(encoding="utf-8"))
    assert len(flows) >= 10
    for name, flow in flows.items():
        assert isinstance(flow["steps"], list), name
        for step in flow["steps"]:
            module = step.get("module")
            if module and module.startswith("workflow:"):
                assert module[9:] in flows
            elif module:
                assert module in REGISTRY, module
            if step.get("workflow"):
                assert step["workflow"] in flows
