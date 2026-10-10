"""R14 child: real, deterministic EVIE v2 HooksGenerator only. No provider paths."""
from __future__ import annotations
import base64
import hashlib
import json
import sys
from pathlib import Path

SCHEMA = "evie.supervised-hooks-worker/1"
MODULE = "hooks_generator"
WORKFLOW = "local_content_hooks_review"
MAX_SCRIPT_BYTES = 8192
MAX_OUTPUT_BYTES = 32768

def generate(payload: dict) -> dict:
    from app.modules_v2.hooks_generator import HooksGenerator
    if not isinstance(payload, dict) or set(payload) != {"topic", "script"}:
        raise ValueError("unsupported worker input")
    topic, script = payload["topic"], payload["script"]
    if (not isinstance(topic, str) or not 1 <= len(topic) <= 80
            or not all(c.isalnum() or c in " -_" for c in topic)
            or not isinstance(script, str)
            or not 20 <= len(script.encode("utf-8")) <= MAX_SCRIPT_BYTES):
        raise ValueError("invalid bounded script or title")
    root = Path.cwd().resolve()
    # Use the REAL checked-in v2 module with a controlled output path.
    result = HooksGenerator().generate(
        topic=topic, run_folder=str(root), sku="EVIEHOOKS",
        tier="review", price_cents=0, platforms=[],
        constraints={"script": script, "output_dir": str(root / "artifacts")},
    )
    paths = getattr(result, "artifacts", [])
    if len(paths) != 1:
        raise ValueError("unexpected hook artifacts")
    path = Path(paths[0])
    if (path.is_symlink() or not path.is_file()
            or not path.resolve().is_relative_to(root)
            or path.stat().st_size > MAX_OUTPUT_BYTES):
        raise ValueError("invalid hook artifact scope or size")
    raw = path.read_bytes()
    hooks = json.loads(raw)
    expected = HooksGenerator()._build_hooks(topic, script)
    if (not isinstance(hooks, dict) or hooks.get("topic") != topic
            or hooks.get("hooks") != expected or len(expected) != 9
            or not isinstance(hooks.get("categories"), dict)
            or hooks["categories"] != {
                "educational": expected[:3],
                "controversial": expected[3:6],
                "curiosity": expected[6:9],
            }):
        raise ValueError("generated hooks did not satisfy the audited template contract")
    return {
        "schemaVersion": SCHEMA,
        "workflow": WORKFLOW,
        "module": MODULE,
        "artifactBase64": base64.b64encode(raw).decode("ascii"),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "scriptSha256": hashlib.sha256(script.encode("utf-8")).hexdigest(),
        "topic": topic,
        "hooks": 9,
        "categories": 3,
    }

def main() -> int:
    try:
        data = json.loads(sys.stdin.buffer.read(10_000).decode("utf-8"))
        print(json.dumps(generate(data), separators=(",", ":")))
        return 0
    except Exception as exc:
        # No dynamic input or filesystem paths in errors.
        print(json.dumps({"schemaVersion": SCHEMA, "status": "failed",
                          "errorType": type(exc).__name__}))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
