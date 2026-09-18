from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from app.modules.base import BaseModule
from .base import ModuleResult


class GumroadPublisher(BaseModule):
    name = "gumroad_publisher"

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
        publish_to_gumroad = bool(merged.get("publish_to_gumroad", True))

        wf_meta = merged.get("workflow_step_metadata") or {}
        product = wf_meta.get("product_packager") or {}
        product_name = merged.get("product_name") or product.get("product_name") or f"{topic} Money Pack"
        description = merged.get("description") or product.get("product_description") or f"{topic} creator bundle"
        artifact_paths = [str(p) for p in (merged.get("artifact_paths") or [])]
        price_raw = merged.get("price") or product.get("price_suggestion") or "$29"

        token = os.getenv("EV_GUMROAD_ACCESS_TOKEN", "")
        status = "skipped"
        product_url = ""
        message = "auto_publish disabled"
        publish_log: dict[str, Any] = {
            "attempted": False,
            "platform": "gumroad",
            "dry_run": dry_run,
            "auto_publish": auto_publish,
            "publish_to_gumroad": publish_to_gumroad,
            "artifact_paths": artifact_paths,
            "started_at": datetime.utcnow().isoformat(),
        }

        def _price_cents(v: Any) -> int:
            if isinstance(v, (int, float)):
                return int(float(v) * 100) if float(v) < 1000 else int(v)
            s = str(v or "").strip().replace("$", "")
            try:
                f = float(s)
                return int(f * 100) if f < 1000 else int(f)
            except Exception:
                return 2900

        if not publish_to_gumroad:
            status = "skipped"
            message = "publish_to_gumroad disabled"
        elif not auto_publish:
            status = "skipped"
            message = "auto_publish disabled"
        elif dry_run:
            status = "simulated"
            product_url = "https://gumroad.example/simulated-product"
            message = "dry_run enabled"
            publish_log.update({"attempted": True, "mode": "dry_run"})
        elif not token:
            status = "missing_credentials"
            message = "EV_GUMROAD_ACCESS_TOKEN not set"
        elif not str(product_name).strip():
            status = "missing_input"
            message = "product_name not provided"
        else:
            publish_log.update({
                "attempted": True,
                "mode": "live",
                "endpoint": "https://api.gumroad.com/v2/products",
            })
            try:
                request_payload = {
                    "access_token": token,
                    "name": product_name,
                    "description": description,
                    "price": _price_cents(price_raw),
                    "published": str(bool(merged.get("publish_live", True))).lower(),
                }
                resp = requests.post(
                    "https://api.gumroad.com/v2/products",
                    data=request_payload,
                    timeout=30,
                )
                publish_log["status_code"] = resp.status_code
                publish_log["request"] = {
                    "name": request_payload["name"],
                    "price": request_payload["price"],
                    "published": request_payload["published"],
                }
                if resp.status_code in (200, 201):
                    body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                    prod = body.get("product") or body.get("resource") or {}
                    product_url = prod.get("short_url") or prod.get("url") or prod.get("preview_url") or ""
                    status = "published" if product_url else "published_no_url"
                    message = "Gumroad product created"
                    publish_log["response"] = {k: prod.get(k) for k in ["id", "name", "short_url", "url"] if k in prod}
                else:
                    status = "api_error"
                    message = f"Gumroad API error {resp.status_code}"
                    publish_log["response_text"] = (resp.text or "")[:800]
            except Exception as exc:
                status = "api_error"
                message = f"Gumroad publish failed: {exc}"
                publish_log["exception"] = str(exc)

        publish_log["completed_at"] = datetime.utcnow().isoformat()
        payload = {
            "topic": topic,
            "status": status,
            "product_name": product_name,
            "product_url": product_url,
            "artifact_paths": artifact_paths,
            "message": message,
            "publish_log": publish_log,
            "generated_at": datetime.utcnow().isoformat(),
        }

        out_dir = Path(merged.get("output_dir") or run_folder)
        out_dir.mkdir(parents=True, exist_ok=True)
        result_path = out_dir / "gumroad_publish_result.json"
        log_path = out_dir / "gumroad_publish_log.json"
        result_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        log_path.write_text(json.dumps(publish_log, indent=2), encoding="utf-8")
        return ModuleResult(name=self.name, artifacts=[str(result_path), str(log_path)], summary=payload)
