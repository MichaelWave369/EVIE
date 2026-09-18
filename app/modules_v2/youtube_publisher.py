from __future__ import annotations

import json
import mimetypes
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from app.modules.base import BaseModule
from .base import ModuleResult


class YoutubePublisher(BaseModule):
    name = "youtube_publisher"

    def generate(
        self,
        *,
        topic: str,
        run_folder: str,
        sku: str,
        tier: str,
        price_cents: int,
        platforms: list[str],
        constraints: dict[str, Any],
    ) -> ModuleResult:
        merged = dict(constraints or {})
        auto_publish = bool(merged.get("auto_publish", False))
        dry_run = bool(merged.get("dry_run", False))
        publish_to_youtube = bool(merged.get("publish_to_youtube", True))

        wf_meta = merged.get("workflow_step_metadata") or {}
        dist = wf_meta.get("distribution_generator") or {}
        title = merged.get("title") or dist.get("youtube_title") or f"{topic} Money Pack"
        description = merged.get("description") or dist.get("youtube_description") or ""

        video_path = str(merged.get("video_path") or merged.get("audio_path") or "")
        access_token = os.getenv("EV_YOUTUBE_ACCESS_TOKEN", "")
        tags = list(merged.get("tags") or dist.get("youtube_tags") or [])

        status = "skipped"
        video_url = ""
        message = "auto_publish disabled"
        publish_log: dict[str, Any] = {
            "attempted": False,
            "platform": "youtube",
            "dry_run": dry_run,
            "auto_publish": auto_publish,
            "publish_to_youtube": publish_to_youtube,
            "video_path": video_path,
            "started_at": datetime.utcnow().isoformat(),
        }

        if not publish_to_youtube:
            status = "skipped"
            message = "publish_to_youtube disabled"
        elif not auto_publish:
            status = "skipped"
            message = "auto_publish disabled"
        elif dry_run:
            status = "simulated"
            video_url = "https://youtube.com/watch?v=simulated"
            message = "dry_run enabled"
            publish_log.update({"attempted": True, "mode": "dry_run"})
        elif not access_token:
            status = "missing_credentials"
            message = "EV_YOUTUBE_ACCESS_TOKEN not set"
        elif not video_path:
            status = "missing_input"
            message = "video_path not provided"
        else:
            path = Path(video_path)
            if not path.exists():
                status = "missing_input"
                message = f"video_path not found: {video_path}"
            else:
                publish_log.update({"attempted": True, "mode": "live"})
                try:
                    metadata = {
                        "snippet": {"title": title, "description": description, "tags": tags},
                        "status": {
                            "privacyStatus": merged.get("privacy_status", "unlisted"),
                            "selfDeclaredMadeForKids": bool(merged.get("made_for_kids", False)),
                        },
                    }
                    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                    file_size = path.stat().st_size
                    init_endpoint = "https://www.googleapis.com/upload/youtube/v3/videos?part=snippet,status&uploadType=resumable"
                    init_resp = requests.post(
                        init_endpoint,
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Content-Type": "application/json; charset=UTF-8",
                            "X-Upload-Content-Length": str(file_size),
                            "X-Upload-Content-Type": media_type,
                        },
                        json=metadata,
                        timeout=30,
                    )
                    publish_log["init_status_code"] = init_resp.status_code
                    if init_resp.status_code not in (200, 201):
                        status = "api_error"
                        message = f"YouTube init upload error {init_resp.status_code}"
                        publish_log["response_text"] = (init_resp.text or "")[:800]
                    else:
                        upload_url = init_resp.headers.get("Location", "")
                        publish_log["upload_url_received"] = bool(upload_url)
                        if not upload_url:
                            status = "api_error"
                            message = "YouTube init upload missing Location header"
                        else:
                            with path.open("rb") as fh:
                                upload_resp = requests.put(
                                    upload_url,
                                    headers={
                                        "Authorization": f"Bearer {access_token}",
                                        "Content-Type": media_type,
                                        "Content-Length": str(file_size),
                                    },
                                    data=fh,
                                    timeout=600,
                                )
                            publish_log["upload_status_code"] = upload_resp.status_code
                            if upload_resp.status_code in (200, 201):
                                body = upload_resp.json() if upload_resp.text else {}
                                vid = body.get("id", "")
                                video_url = f"https://www.youtube.com/watch?v={vid}" if vid else ""
                                status = "published" if vid else "published_no_url"
                                message = "YouTube upload completed"
                                publish_log["response"] = {"id": vid}
                            else:
                                status = "api_error"
                                message = f"YouTube upload error {upload_resp.status_code}"
                                publish_log["response_text"] = (upload_resp.text or "")[:800]
                except Exception as exc:
                    status = "api_error"
                    message = f"YouTube publish failed: {exc}"
                    publish_log["exception"] = str(exc)

        publish_log["completed_at"] = datetime.utcnow().isoformat()
        payload = {
            "topic": topic,
            "status": status,
            "video_url": video_url,
            "title": title,
            "description": description,
            "tags": tags,
            "video_path": video_path,
            "message": message,
            "publish_log": publish_log,
            "generated_at": datetime.utcnow().isoformat(),
        }

        out_dir = Path(merged.get("output_dir") or run_folder)
        out_dir.mkdir(parents=True, exist_ok=True)
        result_path = out_dir / "youtube_publish_result.json"
        log_path = out_dir / "youtube_publish_log.json"
        result_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        log_path.write_text(json.dumps(publish_log, indent=2), encoding="utf-8")
        return ModuleResult(name=self.name, artifacts=[str(result_path), str(log_path)], summary=payload)
