from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import datetime, json
from app.modules.base import ModuleResult
from app.rag.llm import LLM
from app.settings import settings
from app.export.packager import write_text


class BrowserExtensionModule:
    """Generate a browser extension scaffolding + store listing copy (local-only generator)."""
    name = "extension"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        llm = LLM.from_settings()
        ext_name = constraints.get("name", f"{topic} Helper")
        manifest_v = int(constraints.get("manifest_version", 3))
        browser = constraints.get("browser", "chrome-compatible")

        prompt = f"""Create a browser extension blueprint.

Name: {ext_name}
Topic: {topic}
Browser: {browser}
Manifest version: {manifest_v}

Requirements:
- 369 structure: 3 core actions, 6 settings/options, 9 automation hooks
- Provide:
  - manifest.json
  - background/service worker outline
  - content script outline
  - popup UI copy (simple)
  - permissions list
  - store listing copy + keywords + FAQs
- Keep everything privacy-first: no cloud required.
"""
        blueprint = llm.chat([{"role":"user","content":prompt}])

        out_dir = Path(settings.data_dir) / "artifacts" / "extension"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        ext_dir = out_dir / f"extension__{ts}"
        ext_dir.mkdir(parents=True, exist_ok=True)

        write_text(ext_dir / "BLUEPRINT.md", blueprint)

        manifest = {
            "manifest_version": manifest_v,
            "name": ext_name,
            "version": "0.1.0",
            "description": f"{topic} extension (local-first).",
            "action": {"default_popup": "popup.html"},
            "permissions": ["storage"],
            "host_permissions": ["<all_urls>"],
            "background": {"service_worker": "background.js"} if manifest_v == 3 else {"scripts": ["background.js"]},
            "content_scripts": [{"matches": ["<all_urls>"], "js": ["content.js"]}],
        }
        write_text(ext_dir / "manifest.json", json.dumps(manifest, indent=2))

        write_text(ext_dir / "background.js", "// Background worker (generated scaffold)\n")
        write_text(ext_dir / "content.js", "// Content script (generated scaffold)\n")
        write_text(ext_dir / "popup.html", "<!doctype html><html><body><h3>Extension</h3><p>Generated scaffold.</p></body></html>")
        write_text(ext_dir / "popup.js", "// Popup logic\n")

        return ModuleResult(
            artifact_paths=[str(ext_dir / "BLUEPRINT.md"), str(ext_dir / "manifest.json")],
            metadata={"topic": topic, "module": self.name, "ext_dir": str(ext_dir)}
        )
