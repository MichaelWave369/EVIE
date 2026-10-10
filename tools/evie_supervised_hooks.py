"""R14: explicitly confirmed local nine-hook drafting, never a generic runner."""
from __future__ import annotations
import argparse, base64, binascii, hashlib, json, os, shutil, subprocess, sys, tempfile, time
from datetime import datetime, timezone
from pathlib import Path
from app.workflows.preflight import ROOT, read_source, plan_workflow
from tools.evie_qualify import SAFE_ENV_KEYS
from tools.evie_supervised import _stage_directory, _write_new

WORKFLOW = "local_content_hooks_review"
MODULE = "hooks_generator"
SCHEMA = "evie.supervised-hooks-review/1"
SOURCES = ("app/modules_v2/hooks_generator.py", "app/modules/hooks_generator.py", "tools/evie_hooks_worker.py")

def source_check():
    flows, names, digest = read_source()
    if flows.get(WORKFLOW, {}).get("steps") != [{"module": MODULE}]:
        raise ValueError("fixed workflow drift")
    plan = plan_workflow(WORKFLOW, workflows=flows, modules=names, source_digest=digest)
    if len(plan["steps"]) != 1 or plan["summary"]["candidateModules"] != 1 or plan["summary"]["registryProblems"] or plan["executionAuthorized"]:
        raise ValueError("fixed source preflight failed")
    hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCES}
    return plan, digest, hashes

def read_input(path):
    file = Path(path).expanduser()
    if file.is_symlink() or not file.is_file() or not 20 <= file.stat().st_size <= 8192:
        raise ValueError("script must be regular UTF-8 file, 20–8192 bytes")
    script = file.read_bytes().decode("utf-8")
    if len(script.strip()) < 20 or any(ord(c) < 32 and c not in "\r\n\t" for c in script):
        raise ValueError("invalid script")
    return script

def subprocess_run(topic, script, timeout):
    env = {k: os.environ[k] for k in SAFE_ENV_KEYS if k in os.environ}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    cmd = [sys.executable, "-I", "-c",
           "import sys;sys.path.insert(0,sys.argv[1]);from tools.evie_hooks_worker import main;raise SystemExit(main())",
           str(ROOT)]
    with tempfile.TemporaryDirectory(prefix="evie-hooks-") as tmp:
        p = subprocess.run(cmd, cwd=tmp, env=env,
                           input=json.dumps({"topic": topic, "script": script}).encode("utf-8"),
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout)
    if p.returncode != 0 or not 0 < len(p.stdout) <= 60000:
        raise ValueError("child worker rejected request")
    return json.loads(p.stdout.decode("utf-8"))

def validate_child(report, topic, script):
    if not isinstance(report, dict) or any([
        report.get("schemaVersion") != "evie.supervised-hooks-worker/1",
        report.get("workflow") != WORKFLOW, report.get("module") != MODULE,
        report.get("topic") != topic, report.get("hooks") != 9, report.get("categories") != 3,
    ]):
        raise ValueError("worker contract mismatch")
    encoded = report.get("artifactBase64")
    if not isinstance(encoded, str) or len(encoded) > 60000:
        raise ValueError("worker payload invalid")
    try: raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as e: raise ValueError("invalid worker encoding") from e
    if not 0 < len(raw) <= 32768 or hashlib.sha256(raw).hexdigest() != report.get("sha256") or hashlib.sha256(script.encode("utf-8")).hexdigest() != report.get("scriptSha256"):
        raise ValueError("content or script digest mismatch")
    obj = json.loads(raw)
    if not isinstance(obj, dict) or obj.get("topic") != topic:
        raise ValueError("topic mismatch")
    hooks, categories = obj.get("hooks"), obj.get("categories")
    if not isinstance(hooks, list) or len(hooks) != 9 or any(not isinstance(h, str) or not 3 <= len(h) <= 1000 for h in hooks):
        raise ValueError("invalid nine-hook content")
    if not isinstance(categories, dict) or categories != {"educational": hooks[:3], "controversial": hooks[3:6], "curiosity": hooks[6:9]}:
        raise ValueError("invalid category assignments")
    return raw, obj

def review_markdown(obj):
    lines = ["# EVIE Nine Hooks", "", "Local template draft. Fact-check and edit before publishing.", ""]
    for category in ("educational", "controversial", "curiosity"):
        lines.extend(["## " + category.title(), ""])
        for num, item in enumerate(obj["categories"][category], 1):
            safe = item.replace("\r", " ").replace("\n", " ").replace("\t", " ")
            safe = "".join("\\" + c if c in "\\*_{}[]()#+-.!|>" or ord(c) == 96 else c for c in safe)
            lines.append(str(num) + ". " + safe)
        lines.append("")
    return ("\n".join(lines) + "\n").encode("utf-8")

def stage_hooks(*, script_file, topic, stage_dir, confirm, workflow=WORKFLOW, timeout=20):
    if confirm is not True or workflow != WORKFLOW or type(timeout) is not int or not 1 <= timeout <= 20:
        raise ValueError("execution not explicitly authorized for this exact local fixture")
    if not isinstance(topic, str) or not 1 <= len(topic) <= 80 or topic != topic.strip() or not all(c.isalnum() or c in " -_" for c in topic):
        raise ValueError("topic must be 1–80 simple characters")
    script = read_input(script_file)
    destination = _stage_directory(stage_dir)
    plan, workflow_sha, hashes = source_check()
    start = time.monotonic()
    output, parsed = validate_child(subprocess_run(topic, script, timeout), topic, script)
    if source_check() != (plan, workflow_sha, hashes):
        raise ValueError("source changed during run")
    markdown = review_markdown(parsed)
    receipt = {
        "schemaVersion": SCHEMA, "status": "staged_for_human_review",
        "workflow": WORKFLOW, "module": MODULE, "topic": topic,
        "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "origin": "local-unsigned-observation", "workflowSourceSha256": workflow_sha,
        "moduleSourceSha256": hashes[SOURCES[0]], "wrapperSourceSha256": hashes[SOURCES[1]],
        "workerSourceSha256": hashes[SOURCES[2]],
        "scriptSha256": hashlib.sha256(script.encode("utf-8")).hexdigest(),
        "artifactSha256": hashlib.sha256(output).hexdigest(),
        "reviewSheetSha256": hashlib.sha256(markdown).hexdigest(),
        "artifactBytes": len(output), "hookCount": 9, "categoryCount": 3,
        "durationMs": max(0, round((time.monotonic() - start) * 1000)),
        "governance": {
            "localModuleExecuted": True, "legacyRunnerInvoked": False, "databaseTouched": False,
            "llmCalled": False, "providerCredentialsProvided": False, "externalPublishing": False,
            "networkSandboxEnforced": False, "authorizedForFutureRuns": False,
            "humanReviewRequired": True, "signed": False,
        },
        "note": "Unsigned local template run, not authenticated or approved for publishing.",
    }
    bundle = {"nine-hooks.json": output, "nine-hooks-review.md": markdown,
              "workflow-preflight.json": (json.dumps(plan, indent=2) + "\n").encode("utf-8"),
              "review-receipt.json": (json.dumps(receipt, indent=2) + "\n").encode("utf-8")}
    if sum(len(value) for value in bundle.values()) > 100000:
        raise ValueError("review bundle too large")
    destination.mkdir(mode=0o700, exist_ok=False)
    try:
        for name, data in bundle.items(): _write_new(destination / name, data)
    except BaseException:
        shutil.rmtree(destination)
        raise
    return receipt

def main():
    p = argparse.ArgumentParser(description="R14 supervised local nine-hook content draft")
    p.add_argument("workflow", choices=[WORKFLOW])
    p.add_argument("--script-file", required=True)
    p.add_argument("--topic", required=True)
    p.add_argument("--stage-dir", required=True)
    p.add_argument("--confirm-local-execution", action="store_true")
    p.add_argument("--timeout", type=int, default=20)
    args = p.parse_args()
    try:
        print(json.dumps(stage_hooks(script_file=args.script_file, topic=args.topic,
                                     stage_dir=args.stage_dir, confirm=args.confirm_local_execution,
                                     workflow=args.workflow, timeout=args.timeout), indent=2))
        return 0
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError, subprocess.TimeoutExpired):
        print(json.dumps({"schemaVersion": SCHEMA, "status": "failed",
                          "reason": "input-or-supervised-run-rejected", "authorizedForFutureRuns": False}))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
