from __future__ import annotations

import importlib
from pathlib import Path


def _load_bridge(monkeypatch, tmp_path):
    monkeypatch.setenv("EV_VISUAL_FX_BRIDGE_DIR", str(tmp_path / "bridge_data"))
    import tools.visual_fx_bridge as bridge

    bridge = importlib.reload(bridge)
    return bridge


def test_bridge_job_creation_and_status_files(monkeypatch, tmp_path):
    bridge = _load_bridge(monkeypatch, tmp_path)

    src = tmp_path / "input.png"
    src.write_bytes(b"png")

    body = bridge.render_fx_handoff(
        bridge.JobCreate(
            tool_name="render_fx",
            input_paths=[str(src)],
            source_workflow="vault_to_money_pack",
            asset_type="thumbnail",
            job_type="thumbnail_polish",
        )
    )
    job_id = body["job_id"]
    job_dir = Path(body["job_folder"])
    assert job_dir.exists()
    assert (job_dir / "input").exists()
    assert (job_dir / "output").exists()
    assert (job_dir / "meta.json").exists()
    assert (job_dir / "status.json").exists()
    assert (job_dir / "logs.txt").exists()

    meta = (job_dir / "meta.json").read_text(encoding="utf-8")
    assert "awaiting_external_processing" in meta

    fetch = bridge.get_job(job_id)
    assert fetch["job"]["job_id"] == job_id
    assert fetch["job"].get("job_type") == "thumbnail_polish"


def test_bridge_completion_detects_output_files(monkeypatch, tmp_path):
    bridge = _load_bridge(monkeypatch, tmp_path)

    src = tmp_path / "rank.png"
    src.write_bytes(b"png")

    job = bridge.vision_fx_handoff(
        bridge.JobCreate(tool_name="vision_fx", input_paths=[str(src)], asset_type="ranking_review")
    )
    output_file = Path(job["output_folder"]) / "ranked_best.png"
    output_file.write_bytes(b"done")

    inspect = bridge.get_job(job["job_id"])
    assert inspect["job"].get("status") == "output_detected"

    done = bridge.complete_job(job["job_id"], bridge.JobComplete(status="completed", notes="manual done"))
    payload = done["job"]
    assert payload["status"] == "completed"
    assert str(output_file) in payload.get("output_paths", [])


def test_bridge_missing_exe_path_is_graceful(monkeypatch, tmp_path):
    bridge = _load_bridge(monkeypatch, tmp_path)

    monkeypatch.delenv("EV_VECTOR_FX_EXE", raising=False)
    src = tmp_path / "cover.png"
    src.write_bytes(b"png")

    job = bridge.vector_fx_handoff(bridge.JobCreate(tool_name="vector_fx", input_paths=[str(src)]))
    assert job.get("status") == "awaiting_external_processing"
    assert (job.get("launch") or {}).get("launched") is False


def test_bridge_auto_complete_when_enabled(monkeypatch, tmp_path):
    monkeypatch.setenv("EV_VISUAL_FX_AUTO_COMPLETE_ON_OUTPUT", "true")
    bridge = _load_bridge(monkeypatch, tmp_path)

    src = tmp_path / "social.png"
    src.write_bytes(b"png")
    job = bridge.render_fx_handoff(bridge.JobCreate(tool_name="render_fx", input_paths=[str(src)]))
    output_file = Path(job["output_folder"]) / "done.png"
    output_file.write_bytes(b"ok")

    inspect = bridge.get_job(job["job_id"])
    assert inspect["job"].get("status") == "completed"
    assert inspect.get("auto_completed") is True


def test_bridge_approve_marks_preferred_final_asset(monkeypatch, tmp_path):
    bridge = _load_bridge(monkeypatch, tmp_path)

    src = tmp_path / "thumb.png"
    src.write_bytes(b"png")
    final_state = tmp_path / "final_assets.json"

    job = bridge.vision_fx_handoff(
        bridge.JobCreate(
            tool_name="vision_fx",
            input_paths=[str(src)],
            metadata={"final_assets_state_path": str(final_state), "final_asset_category": "final_thumbnail"},
        )
    )
    output_file = Path(job["output_folder"]) / "approved.png"
    output_file.write_bytes(b"ok")

    approved = bridge.approve_job_asset(job["job_id"], bridge.JobApprove(category="final_thumbnail", asset_path=str(output_file), mark_completed=True))
    assert approved["job"].get("approved_final_asset") == str(output_file)
    assert approved["job"].get("status") == "completed"
    assert final_state.exists()
