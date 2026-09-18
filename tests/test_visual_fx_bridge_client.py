from __future__ import annotations

from app.local_services.visual_fx_bridge_client import VisualFXBridgeClient


def test_bridge_client_unavailable_fallback():
    client = VisualFXBridgeClient(base_url="http://127.0.0.1:59999", timeout=1)
    health = client.health()
    assert health.get("ok") is False

    handoff = client.submit_handoff(tool_name="render_fx", input_paths=["/tmp/missing.png"])
    assert handoff.get("ok") is False
