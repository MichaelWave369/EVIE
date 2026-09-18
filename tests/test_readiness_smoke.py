from __future__ import annotations

from types import SimpleNamespace

from app.ops.readiness import run_readiness_checks
from app.ops import smoke


def test_readiness_checks_runs(monkeypatch, tmp_path):
    monkeypatch.setenv("EV_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("EV_DB_PATH", str(tmp_path / "data" / "embervault.db"))
    monkeypatch.setenv("EV_LLM_BACKEND", "openai")
    monkeypatch.setenv("EV_OPENAI_API_KEY", "x")
    monkeypatch.setenv("EV_EMBED_BACKEND", "hash")

    class _Resp:
        def __init__(self, status_code):
            self.status_code = status_code

    monkeypatch.setattr("app.ops.readiness.requests.get", lambda *a, **k: _Resp(200))
    out = run_readiness_checks()
    assert out.get("overall") in {"pass", "warn"}
    names = {c.get("name") for c in out.get("checks", [])}
    assert "core_paths" in names
    assert "comfyui" in names
    assert "visual_fx_bridge" in names


class _OkMod:
    def generate(self, topic, constraints):
        return SimpleNamespace(artifact_paths=["a.json"], metadata={})


def test_smoke_runner_reports_targets(monkeypatch):
    monkeypatch.setattr(smoke, "REGISTRY", {name: _OkMod() for name in smoke.SMOKE_MODULE_TARGETS})
    monkeypatch.setattr(smoke.runner, "run_workflow", lambda name, **kwargs: {"steps": [{"module": name}]})
    out = smoke.run_smoke_tests(topic="T")
    assert out.get("overall") in {"pass", "warn"}
    targets = {r.get("target") for r in out.get("results", [])}
    for m in smoke.SMOKE_MODULE_TARGETS:
        assert m in targets
    for w in smoke.SMOKE_WORKFLOW_TARGETS:
        assert w in targets
