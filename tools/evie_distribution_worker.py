"""R15 child: actual v2 DistributionGenerator using SHA-checked R14 hook metadata."""
from __future__ import annotations
import base64, hashlib, json, sys
from pathlib import Path

SCHEMA="evie.distribution-worker/1"
MAX_BYTES=32768

def generate(request):
    from app.modules_v2.distribution_generator import DistributionGenerator
    if not isinstance(request,dict) or set(request)!={"topic","hooks"}:
        raise ValueError("request schema denied")
    topic, hooks=request["topic"],request["hooks"]
    if (not isinstance(topic,str) or not 1<=len(topic)<=80 or
        not all(c.isalnum() or c in " -_" for c in topic) or
        not isinstance(hooks,list) or len(hooks)!=9 or
        any(not isinstance(h,str) or not 3<=len(h)<=1000 for h in hooks)):
        raise ValueError("invalid approved hook payload")
    root=Path.cwd().resolve()
    result=DistributionGenerator().generate(
        topic=topic,run_folder=str(root),sku="EVIEDISTREVIEW",tier="review",
        price_cents=0,platforms=[],constraints={
            "output_dir":str(root/"drafts"),
            "workflow_step_metadata":{"hooks_generator":{"hooks":hooks}},
        },
    )
    paths=getattr(result,"artifacts",[])
    if len(paths)!=1: raise ValueError("unexpected module output count")
    file=Path(paths[0])
    if (file.is_symlink() or not file.is_file() or
        not file.resolve().is_relative_to(root) or
        not 0<file.stat().st_size<=MAX_BYTES):
        raise ValueError("module wrote unexpected artifact")
    content=file.read_bytes()
    body=json.loads(content)
    if (body.get("topic")!=topic or body.get("hooks_used")!=hooks[:5] or
        body.get("tiktok_hooks")!=hooks[:5] or
        not isinstance(body.get("twitter_thread"),list)):
        raise ValueError("distribution module failed hook handoff contract")
    return {
        "schemaVersion":SCHEMA,"module":"distribution_generator",
        "sha256":hashlib.sha256(content).hexdigest(),
        "artifactBase64":base64.b64encode(content).decode("ascii"),
        "inputHooksSha256":hashlib.sha256(json.dumps(hooks,ensure_ascii=False,separators=(",",":")).encode()).hexdigest(),
        "hooksConsumed":5,
    }

def main():
    try:
        request=json.loads(sys.stdin.buffer.read(20000).decode("utf-8"))
        print(json.dumps(generate(request),separators=(",",":")))
        return 0
    except Exception as exc:
        print(json.dumps({"schemaVersion":SCHEMA,"status":"failed","errorType":type(exc).__name__}))
        return 1

if __name__=="__main__":
    raise SystemExit(main())
