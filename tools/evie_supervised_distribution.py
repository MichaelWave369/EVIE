"""R15: SHA-pinned manual checkpoint before real local DistributionGenerator.

No unattended orchestration. Stage 1 is the independently invoked R14 run.
Only the operator who supplies --approved-hooks-sha256 and --confirm-local-execution
may request the local second step. This is an explicit user gesture, not
cryptographic identity or an independently trusted human signature.
"""
from __future__ import annotations

import argparse, base64, binascii, hashlib, json, os, shutil, subprocess, sys, tempfile, time
from datetime import datetime, timezone
from pathlib import Path
from app.workflows.preflight import ROOT, read_source, plan_workflow
from tools.evie_qualify import SAFE_ENV_KEYS
from tools.evie_supervised import _stage_directory, _write_new
from tools import evie_supervised_hooks as prior

WORKFLOW="local_hooks_to_distribution_review"
SOURCE_WORKFLOW="local_content_hooks_review"
SCHEMA="evie.supervised-distribution-review/1"
REVIEW_SCHEMA="evie.supervised-hooks-review/1"
FILES=("app/modules_v2/distribution_generator.py","app/modules/distribution_generator.py","tools/evie_distribution_worker.py")
MAX_SECONDS=20
MAX_BUNDLE=110000

def _source_check():
    flows,modules,digest=read_source()
    if (flows.get(WORKFLOW,{}).get("steps")!=[
            {"module":"hooks_generator"},{"module":"distribution_generator"}] or
        flows.get(SOURCE_WORKFLOW,{}).get("steps")!=[{"module":"hooks_generator"}]):
        raise ValueError("reviewed two-step workflow source has drifted")
    plan=plan_workflow(WORKFLOW,workflows=flows,modules=modules,source_digest=digest,enabled_flags=[])
    if (len(plan["steps"])!=2 or
        [x["name"] for x in plan["steps"]] != ["hooks_generator","distribution_generator"] or
        plan["summary"]["candidateModules"]!=2 or plan["summary"]["registryProblems"] or
        plan["executionAuthorized"] or plan["executed"]):
        raise ValueError("source preflight did not pass")
    hashes={file:hashlib.sha256((ROOT/file).read_bytes()).hexdigest() for file in FILES}
    return plan,digest,hashes

def _regular_bytes(path,limit):
    file=Path(path)
    if not file.is_file() or file.is_symlink() or not 0<file.stat().st_size<=limit:
        raise ValueError("review input missing, symlink or over size limit")
    return file.read_bytes()

def _load_approved_first_stage(folder,approved_sha,expected_source):
    if not isinstance(approved_sha,str) or len(approved_sha)!=64 or any(c not in "0123456789abcdef" for c in approved_sha):
        raise ValueError("explicit SHA-256 approval must be exactly 64 lowercase hexadecimal characters")
    root=Path(folder).expanduser()
    if not root.is_dir() or root.is_symlink():
        raise ValueError("R14 handoff folder must be a regular directory")
    # R14 outputs were staged outside checkout by its own explicit gate.
    receipt=json.loads(_regular_bytes(root/"review-receipt.json",32000))
    payload=_regular_bytes(root/"nine-hooks.json",32768)
    if not isinstance(receipt,dict) or receipt.get("schemaVersion")!=REVIEW_SCHEMA or receipt.get("status")!="staged_for_human_review" or receipt.get("workflow")!=SOURCE_WORKFLOW or receipt.get("module")!="hooks_generator":
        raise ValueError("unsupported first-stage receipt")
    flags=receipt.get("governance")
    if not isinstance(flags,dict) or any([
        flags.get("localModuleExecuted") is not True,
        flags.get("legacyRunnerInvoked") is not False,
        flags.get("databaseTouched") is not False,
        flags.get("llmCalled") is not False,
        flags.get("providerCredentialsProvided") is not False,
        flags.get("externalPublishing") is not False,
        flags.get("authorizedForFutureRuns") is not False,
        flags.get("signed") is not False,
    ]):
        raise ValueError("first-stage receipt claims unsupported authority")
    actual=hashlib.sha256(payload).hexdigest()
    if (actual!=approved_sha or actual!=receipt.get("artifactSha256") or
        len(payload)!=receipt.get("artifactBytes") or
        receipt.get("workflowSourceSha256")!=expected_source):
        raise ValueError("R14 artifact SHA-256, source revision or operator approval mismatch")
    first_sources=prior.source_check()[2]
    for key,field in (
        (prior.SOURCES[0],"moduleSourceSha256"),
        (prior.SOURCES[1],"wrapperSourceSha256"),
        (prior.SOURCES[2],"workerSourceSha256"),
    ):
        if receipt.get(field)!=first_sources[key]:
            raise ValueError("first-stage source no longer matches local producer")
    hooks=json.loads(payload)
    topic=hooks.get("topic") if isinstance(hooks,dict) else None
    lines=hooks.get("hooks") if isinstance(hooks,dict) else None
    groups=hooks.get("categories") if isinstance(hooks,dict) else None
    if (not isinstance(topic,str) or topic!=receipt.get("topic") or
        not isinstance(lines,list) or len(lines)!=9 or
        any(not isinstance(h,str) or not 3<=len(h)<=1000 for h in lines) or
        not isinstance(groups,dict) or groups!={"educational":lines[:3],
                 "controversial":lines[3:6],"curiosity":lines[6:9]}):
        raise ValueError("first-stage nine-hook contract invalid")
    return topic,lines,actual

def _run_second_step(topic,hooks,seconds):
    env={key:os.environ[key] for key in SAFE_ENV_KEYS if key in os.environ}
    env["PYTHONDONTWRITEBYTECODE"]="1"
    cmd=[sys.executable,"-I","-c",
         "import sys;sys.path.insert(0,sys.argv[1]);from tools.evie_distribution_worker import main;raise SystemExit(main())",
         str(ROOT)]
    with tempfile.TemporaryDirectory(prefix="evie-distribution-") as temporary:
        proc=subprocess.run(cmd,cwd=temporary,env=env,
                            input=json.dumps({"topic":topic,"hooks":hooks}).encode("utf-8"),
                            stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                            timeout=seconds,check=False)
    if proc.returncode!=0 or not 0<len(proc.stdout)<=60000:
        raise ValueError("bounded distribution step failed")
    return json.loads(proc.stdout.decode("utf-8"))

def _validate_second(response,topic,hooks):
    if (not isinstance(response,dict) or response.get("schemaVersion")!="evie.distribution-worker/1" or
        response.get("module")!="distribution_generator" or response.get("hooksConsumed")!=5):
        raise ValueError("second-stage protocol changed")
    encoded=response.get("artifactBase64")
    if not isinstance(encoded,str) or len(encoded)>60000:
        raise ValueError("second-stage artifact too large")
    try:
        payload=base64.b64decode(encoded,validate=True)
    except (ValueError,binascii.Error) as exc:
        raise ValueError("second-stage artifact encoding invalid") from exc
    hook_sha=hashlib.sha256(json.dumps(hooks,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
    if not 0<len(payload)<=32768 or response.get("sha256")!=hashlib.sha256(payload).hexdigest() or response.get("inputHooksSha256")!=hook_sha:
        raise ValueError("second-stage digest mismatch")
    body=json.loads(payload)
    if (not isinstance(body,dict) or body.get("topic")!=topic or
        body.get("hooks_used")!=hooks[:5] or body.get("tiktok_hooks")!=hooks[:5] or
        not isinstance(body.get("twitter_thread"),list) or len(body["twitter_thread"])<1):
        raise ValueError("real distribution module did not consume approved first five hooks")
    return payload,body

def stage_distribution(*,hooks_dir,approved_hooks_sha256,stage_dir,confirm,timeout=MAX_SECONDS,worker_backend=None):
    if confirm is not True:
        raise ValueError("second step requires operator confirmation")
    if type(timeout) is not int or not 1<=timeout<=MAX_SECONDS:
        raise ValueError("second step exceeds time budget")
    destination=_stage_directory(stage_dir)
    plan,source_sha,hashes=_source_check()
    topic,hooks,input_sha=_load_approved_first_stage(hooks_dir,approved_hooks_sha256,source_sha)
    started=time.monotonic()
    artifact,body=_validate_second((worker_backend or _run_second_step)(topic,hooks,timeout),topic,hooks)
    if _source_check()!=(plan,source_sha,hashes):
        raise ValueError("source changed during generation")
    # Re-read source artifact immediately before staging. Refuse changed inputs.
    if _load_approved_first_stage(hooks_dir,approved_hooks_sha256,source_sha)[2]!=input_sha:
        raise ValueError("approved source changed during generation")
    receipt={
        "schemaVersion":SCHEMA,"status":"staged_for_human_review",
        "workflow":WORKFLOW,"completedStage":"distribution_generator",
        "topic":topic,"origin":"local-unsigned-observation",
        "createdAt":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
        "workflowSourceSha256":source_sha,"distributionSourceSha256":hashes[FILES[0]],
        "distributionWrapperSha256":hashes[FILES[1]],"workerSourceSha256":hashes[FILES[2]],
        "approvedInputSha256":input_sha,
        "distributionSha256":hashlib.sha256(artifact).hexdigest(),
        "distributionBytes":len(artifact),"hooksConsumed":5,
        "durationMs":max(0,round((time.monotonic()-started)*1000)),
        "governance":{
            "operatorConfirmedExactDigest":True,
            "operatorIdentityVerified":False,
            "humanSignatureVerified":False,
            "localSecondModuleExecuted":True,
            "legacyRunnerInvoked":False,"databaseTouched":False,"llmCalled":False,
            "providerCredentialsProvided":False,"externalPublishing":False,
            "networkSandboxEnforced":False,"furtherExecutionAuthorized":False,
            "editorialApprovalGranted":False,"signed":False,
        },
        "note":"SHA-confirmed local handoff, not an authenticated approval or permission to publish.",
    }
    files={"distribution-draft.json":artifact,
           "workflow-preflight.json":(json.dumps(plan,indent=2)+"\n").encode(),
           "distribution-review-receipt.json":(json.dumps(receipt,indent=2)+"\n").encode()}
    if sum(map(len,files.values()))>MAX_BUNDLE:
        raise ValueError("staged bundle exceeds budget")
    destination.mkdir(mode=0o700,exist_ok=False)
    try:
        for name,data in files.items(): _write_new(destination/name,data)
    except BaseException:
        shutil.rmtree(destination)
        raise
    return receipt

def main():
    parser=argparse.ArgumentParser(description="R15: manually approve first-stage digest before offline distribution drafting")
    parser.add_argument("--hooks-dir",required=True)
    parser.add_argument("--approved-hooks-sha256",required=True)
    parser.add_argument("--stage-dir",required=True)
    parser.add_argument("--confirm-local-execution",action="store_true")
    parser.add_argument("--timeout",type=int,default=MAX_SECONDS)
    args=parser.parse_args()
    try:
        print(json.dumps(stage_distribution(hooks_dir=args.hooks_dir,
              approved_hooks_sha256=args.approved_hooks_sha256,
              stage_dir=args.stage_dir,confirm=args.confirm_local_execution,
              timeout=args.timeout),indent=2))
        return 0
    except (ValueError,OSError,UnicodeError,json.JSONDecodeError,subprocess.TimeoutExpired):
        print(json.dumps({"schemaVersion":SCHEMA,"status":"failed",
                          "reason":"approval-or-fixed-run-rejected",
                          "furtherExecutionAuthorized":False}))
        return 1
if __name__=="__main__":
    raise SystemExit(main())
