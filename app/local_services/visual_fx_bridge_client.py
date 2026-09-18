from __future__ import annotations

import os
from typing import Any

import requests


class VisualFXBridgeClient:
    def __init__(self, base_url: str | None = None, timeout: int = 10) -> None:
        self.base_url = (base_url or os.getenv("EV_VISUAL_FX_BRIDGE_URL") or "http://127.0.0.1:18888").rstrip("/")
        self.timeout = int(timeout)

    def health(self) -> dict[str, Any]:
        try:
            r = requests.get(f"{self.base_url}/health", timeout=self.timeout)
            if r.status_code == 200:
                return {"ok": True, "data": r.json()}
            return {"ok": False, "status_code": r.status_code, "error": r.text[:500]}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def recent_jobs(self, limit: int = 10) -> dict[str, Any]:
        try:
            r = requests.get(f"{self.base_url}/jobs", params={"limit": int(limit)}, timeout=self.timeout)
            if r.status_code == 200:
                return {"ok": True, "jobs": (r.json() or {}).get("jobs", [])}
            return {"ok": False, "status_code": r.status_code, "error": r.text[:500]}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def submit_handoff(
        self,
        *,
        tool_name: str,
        input_paths: list[str],
        source_workflow: str = "",
        source_run_id: str = "",
        asset_type: str = "",
        prompts_used: list[str] | None = None,
        ranking_notes: list[str] | None = None,
        expected_outputs: list[str] | None = None,
        notes: str = "",
        metadata: dict[str, Any] | None = None,
        job_type: str = "",
    ) -> dict[str, Any]:
        payload = {
            "tool_name": tool_name,
            "input_paths": input_paths or [],
            "source_workflow": source_workflow,
            "source_run_id": source_run_id,
            "asset_type": asset_type,
            "prompts_used": prompts_used or [],
            "ranking_notes": ranking_notes or [],
            "expected_outputs": expected_outputs or [],
            "notes": notes,
            "metadata": metadata or {},
            "job_type": job_type,
        }
        path = f"/{tool_name.replace('_', '-')}/handoff"
        try:
            r = requests.post(f"{self.base_url}{path}", json=payload, timeout=self.timeout)
            if r.status_code in (200, 201):
                return {"ok": True, "job": r.json()}
            return {"ok": False, "status_code": r.status_code, "error": r.text[:500], "payload": payload}
        except Exception as e:
            return {"ok": False, "error": str(e), "payload": payload}

    def approve_asset(self, job_id: str, *, category: str = "", asset_path: str = "", note: str = "", mark_completed: bool = True) -> dict[str, Any]:
        payload = {"category": category, "asset_path": asset_path, "note": note, "mark_completed": bool(mark_completed)}
        try:
            r = requests.post(f"{self.base_url}/jobs/{job_id}/approve", json=payload, timeout=self.timeout)
            if r.status_code in (200, 201):
                return {"ok": True, "data": r.json()}
            return {"ok": False, "status_code": r.status_code, "error": r.text[:500], "payload": payload}
        except Exception as e:
            return {"ok": False, "error": str(e), "payload": payload}
