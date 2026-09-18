from __future__ import annotations

from pathlib import Path
from typing import Any

from app.local_services.visual_fx_bridge_client import VisualFXBridgeClient


class _BaseConnector:
    tool_name = "tool"

    def __init__(self) -> None:
        self.client = VisualFXBridgeClient()

    def _submit(self, *, input_paths: list[str], asset_type: str, prompts_used: list[str], ranking_notes: list[str], expected_outputs: list[str], notes: str, metadata: dict[str, Any] | None = None, job_type: str = "") -> dict[str, Any]:
        return self.client.submit_handoff(
            tool_name=self.tool_name,
            input_paths=input_paths,
            asset_type=asset_type,
            prompts_used=prompts_used,
            ranking_notes=ranking_notes,
            expected_outputs=expected_outputs,
            notes=notes,
            metadata=metadata or {},
            job_type=job_type,
        )


class RenderFXConnector(_BaseConnector):
    tool_name = "render_fx"

    def enhance(self, image_paths: list[str], *, output_dir: Path, style: str, job_type: str = "thumbnail_polish", final_assets_state_path: str = "", final_asset_category: str = "") -> dict[str, Any]:
        output_dir.mkdir(parents=True, exist_ok=True)
        res = self._submit(
            input_paths=list(image_paths),
            asset_type="image_enhancement",
            prompts_used=[f"render polish style={style}"],
            ranking_notes=[],
            expected_outputs=["enhanced image(s) copied into output folder"],
            notes="Manual/desktop Render FX handoff created by EVIE.",
            metadata={"style": style, "output_dir": str(output_dir), "final_assets_state_path": final_assets_state_path, "final_asset_category": final_asset_category},
            job_type=job_type,
        )
        if not res.get("ok"):
            return {
                "status": "unavailable",
                "enhanced_paths": list(image_paths),
                "message": f"Bridge unavailable for Render FX handoff: {res.get('error', 'unknown error')}",
            }
        job = res.get("job") or {}
        return {
            "status": "awaiting_external_processing",
            "enhanced_paths": list(image_paths),
            "job_id": job.get("job_id"),
            "job_folder": job.get("job_folder"),
            "output_folder": job.get("output_folder"),
            "message": "Render FX handoff job created. Add refined assets to output/ and mark complete via bridge.",
        }


class VisionFXConnector(_BaseConnector):
    tool_name = "vision_fx"

    def rank(self, image_paths: list[str], *, topic: str, title: str, hook: str, job_type: str = "thumbnail_rank", final_assets_state_path: str = "", final_asset_category: str = "") -> dict[str, Any]:
        res = self._submit(
            input_paths=list(image_paths),
            asset_type="ranking_review",
            prompts_used=[f"topic={topic}", f"title={title}", f"hook={hook}"],
            ranking_notes=[],
            expected_outputs=["ranking_notes", "selected/best image"],
            notes="Manual/desktop Vision FX ranking handoff.",
            metadata={"topic": topic, "title": title, "hook": hook, "final_assets_state_path": final_assets_state_path, "final_asset_category": final_asset_category},
            job_type=job_type,
        )
        if not res.get("ok"):
            return {
                "status": "unavailable",
                "message": f"Bridge unavailable for Vision FX handoff: {res.get('error', 'unknown error')}",
                "todo": "Run bridge service or keep fallback ranking.",
            }
        job = res.get("job") or {}
        return {
            "status": "awaiting_external_processing",
            "job_id": job.get("job_id"),
            "job_folder": job.get("job_folder"),
            "output_folder": job.get("output_folder"),
            "message": "Vision FX handoff job created. Add ranking notes/outputs then mark complete.",
        }


class VectorFXConnector(_BaseConnector):
    tool_name = "vector_fx"

    def polish(self, image_paths: list[str], *, output_dir: Path, job_type: str = "social_visual_finish", final_assets_state_path: str = "", final_asset_category: str = "") -> dict[str, Any]:
        output_dir.mkdir(parents=True, exist_ok=True)
        res = self._submit(
            input_paths=list(image_paths),
            asset_type="vector_polish",
            prompts_used=[],
            ranking_notes=[],
            expected_outputs=["overlay/polished image(s)"],
            notes="Manual/desktop Vector FX handoff created by EVIE.",
            metadata={"output_dir": str(output_dir), "final_assets_state_path": final_assets_state_path, "final_asset_category": final_asset_category},
            job_type=job_type,
        )
        if not res.get("ok"):
            return {
                "status": "unavailable",
                "polished_paths": list(image_paths),
                "message": f"Bridge unavailable for Vector FX handoff: {res.get('error', 'unknown error')}",
            }
        job = res.get("job") or {}
        return {
            "status": "awaiting_external_processing",
            "polished_paths": list(image_paths),
            "job_id": job.get("job_id"),
            "job_folder": job.get("job_folder"),
            "output_folder": job.get("output_folder"),
            "message": "Vector FX handoff job created. Save polished files in output/ and complete job.",
        }
