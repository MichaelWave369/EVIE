# EVIE R18: Governed Two-Stage Content Flow Console

## State machine

R18 coordinates the existing real source workflow `local_hooks_to_distribution_review` (exactly `hooks_generator` then `distribution_generator`) without expanding EVIE's executor allowlist. It does not use the legacy database-writing workflow runner.

| Event | State | Execution |
|---|---|---|
| `01-hooks-paused.json` | `paused_for_human_review` | Genuine local R14 hooks generated; no signed approval or stage 2 |
| `02-signed-resume-attempt.json` | `resume_attempt_recorded` | Marker written before signed Docker second-stage attempt; outcome may be uncertain |
| `03-distribution-staged.json` | `distribution_staged_for_review` | Genuine R17 isolated generator produced review-only drafts; NOT published or editorially accepted |

All three event files use exclusive creation. They are unsigned, local and mutable by users with filesystem access, not tamper-proof attestations.

## Commands: separate operator gestures

From a trusted local EVIE checkout (outside Docker for Stage 1), supply your own `draft.txt` UTF-8 content with 20–8192 bytes:

    python -m tools.evie_governed_flow plan

The plan command is read-only. To run only Stage 1 and pause:

    python -m tools.evie_governed_flow start --session-dir ../evie-flow-session-001 --script-file ./draft.txt --topic "EVIE Creator Loop" --confirm-local-execution

Create a new session directory each time, outside Git. This invokes the existing R14 local generator exactly once, stages the nine hooks in `evie-flow-session-001/hooks/`, emits event 01 and STOPS. The R14 host Python subprocess is not OS-sandboxed.

Review and fact-check `hooks/nine-hooks.json`. If a draft is unacceptable, fix your own input and start a new session. Modifying the staged artifact invalidates its digest.

    python -m tools.evie_governed_flow status --session-dir ../evie-flow-session-001

`status` reads the original artifact, source revision and event records; it never invokes a module or Docker.

After personally reviewing the original nine hooks, generate a signed R16 approval using your encrypted signing key (key setup is described in R16). The lease must bind the exact current R14 artifact SHA-256 and **the yet-to-exist** `session/distribution` path:

    python -m tools.evie_action_lease issue --hooks-dir ../evie-flow-session-001/hooks --approved-hooks-sha256 YOUR_REVIEWED_64_CHARACTER_SHA256 --stage-dir ../evie-flow-session-001/distribution --signing-key ../evie-lease-private.pem --lease-file ../evie-flow-lease-001.json

Lease issuance is independent, interactive, and does not execute Stage 2. The signed lease usually expires in five minutes (maximum ten).

Resume only after separately supplying a trusted public key, persistent single-host nonce ledger and explicit confirmation:

    python -m tools.evie_governed_flow resume --session-dir ../evie-flow-session-001 --lease-file ../evie-flow-lease-001.json --trusted-public ../evie-lease-trusted-public.pem --ledger ../evie-local-lease-ledger.sqlite --confirm-local-execution

R18 checks original R14 file bytes, source provenance and the signed action/destination/TTL/budget; it checks that Docker and the local image are available **before** writing event 02. It then exclusively creates event 02 to reject concurrent attempts, and calls R17's signed, offline, read-only Docker execution path. R17 independently checks the lease again, atomically consumes its nonce, and generates the real distribution artifact. R18 then writes event 03 binding the output digest to the approved first-stage digest and signed lease nonce.

## Failure and retry policy

- Missing Docker, invalid signature, wrong destination or changed source/artifact: reject before event 02 and before spending the nonce (where the preflight check catches it).
- After event 02, a crash, failed stage, timeout or stopped process leaves the state as `resume_attempt_recorded` (outcome UNKNOWN). No automatic retry, deletion or reset command exists. Start a NEW session with new output directory and fresh approval if you need to retry.
- `distribution_staged_for_review` is NOT final DONE, accepted claims, publishing authority, emailing, scheduling, or an externally authenticated result.
- The R16 nonce's one-use property applies only to one intact local SQLite ledger. Host compromise or use of older R15/R16 paths bypasses this optional controller.
- The event documents are self-reports; there is no human identity verification, background daemon, remote queue or universal arbitrary-job permission.

## Tests and CI

Run `pytest -q tests/test_governed_flow.py` for real R14 output, deterministic real v2 distribution through a mocked container adapter, invalid state/source/artifact/approval refusals, no Docker refusal and irreversible attempt markers. A mock is NOT sandbox evidence.

CI's existing `EVIE R17 Offline Docker Capsule` workflow now additionally runs a genuine R18 start → independent signed R16 lease → R17 Docker-only resumed distribution step. The same CI continues its explicit external-network denial test. Do not merge without that real-container green result, alongside the full Python gate and React tests.

## Next

Before using a future autonomous controller, add an isolated Stage 1, independent identity/approval verification and an enforced one-host service that no other CLI can bypass. Current R18 remains manual and local-only.
