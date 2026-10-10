# EVIE R21: Default Safe Entry and Legacy Execution Migration

## What R21 changes (and does not change)

New EVIE content workflows get one **recommended local CLI**: `python -m tools.evie_safe`. This is a fixed, transparent wrapper over the already audited R19 governed controller and R20 read-only auditor. Its parser accepts only `policy`, `entrypoints`, `plan`, `start`, `status`, `resume`, and `audit`. There is no user-selectable module, arbitrary command argument, generic subprocess, publication method, daemon, automated signing or fallback to a weaker host runner.

The wrapper is a convenient **default boundary for callers that voluntarily use it**. It is not a new operating-system permission mechanism. The old direct CLIs and other Python entrypoints are still callable by people with access to the repository. This is an intentional, backward-compatible migration, not a security claim that all legacy execution has been disabled.

## Safe-entry command contract

From a trusted EVIE checkout with dependencies installed:

| Command | What it does | Mutation and authorization |
|---|---|---|
| `python -m tools.evie_safe policy` | Audit the six known direct entrypoints and migration disposition | Read-only; acknowledges legacy host bypasses |
| `python -m tools.evie_safe entrypoints` | Reuse R20's source SHA inventory | Read-only, not exhaustive |
| `python -m tools.evie_safe plan` | Show the exact R19 hooks → distribution governed source plan | No worker, no file writes |
| `python -m tools.evie_safe start ...` | Run real HooksGenerator in offline Docker then hard-pause | Requires explicit operator confirmation, Docker image preinstalled, new session folder |
| `python -m tools.evie_safe status ...` | Inspect a paused, attempted or draft-staged session | Read-only; never replays a worker |
| `python -m tools.evie_safe resume ...` | Separately signed R16 one-use approval + real R17 Docker distribution draft | Requires operator confirmation, independently supplied trusted public key, lease and intact SQLite nonce ledger |
| `python -m tools.evie_safe audit ...` | Reuse R20 completion-evidence inspector | Read-only source/hashes; optional independent historic lease/ledger verification; never final product DONE |

## Real operator flow

Preflight first:

    python -m tools.evie_safe policy
    python -m tools.evie_safe plan

Have Docker Desktop/Engine running and explicitly preload your trusted local image yourself (`docker pull python:3.11-slim`). EVIE will never install Docker or download a runtime automatically. Prepare a 20–8192-byte UTF-8 script file, then start **once**:

    python -m tools.evie_safe start --session-dir ../evie-flow-session-001 --script-file ./draft.txt --topic "EVIE Creator Loop" --confirm-local-execution

Inspect `../evie-flow-session-001/hooks/nine-hooks.json` and `01-hooks-paused.json` and check:

    python -m tools.evie_safe status --session-dir ../evie-flow-session-001

Check the original `artifactSha256` yourself. Correct errors by improving the original script and creating a fresh session. Do NOT directly edit hashed first-stage files and bypass the review check.

**The safe-entry wrapper does not sign leases.** Once you're satisfied with the first stage, separately authorize an exact second-stage attempt with the existing encrypted Ed25519 signing key and short TTL:

    python -m tools.evie_action_lease issue --hooks-dir ../evie-flow-session-001/hooks --approved-hooks-sha256 YOUR_REVIEWED_64_CHARACTER_SHA256 --stage-dir ../evie-flow-session-001/distribution --signing-key ../evie-lease-private.pem --lease-file ../evie-flow-lease-001.json

Then explicitly consume that signed lease to resume with the original real distribution module inside offline Docker:

    python -m tools.evie_safe resume --session-dir ../evie-flow-session-001 --lease-file ../evie-flow-lease-001.json --trusted-public ../evie-lease-trusted-public.pem --ledger ../evie-local-lease-ledger.sqlite --confirm-local-execution

Finally, audit the local completion evidence without executing or spending anything:

    python -m tools.evie_safe audit --session-dir ../evie-flow-session-001 --lease-file ../evie-flow-lease-001.json --trusted-public ../evie-lease-trusted-public.pem --ledger ../evie-local-lease-ledger.sqlite

A verified local draft is NOT published, fact-checked editorial acceptance, remote receipt, or final DONE.

## Migration inventory and policy

The `policy` command includes SHA-256 for six known direct entrypoints, tagging the **four legacy host-subprocess commands** `evie_supervised` (CAD fixture), `evie_supervised_hooks` (hooks), `evie_supervised_distribution` (hash-only distribution), and `evie_approved_distribution` (signed but host-executed distribution) as `legacy_compatibility_only_not_restricted_by_this_cli`.

The R17 direct isolated distribution CLI stays available as `direct_advanced_opt_in`; the governed dual-Docker controller also stays available as `direct_advanced_opt_in`. Neither is disabled. There is **no** source removal, migration of old staged receipts, silent reassignment of permissions, redirection of legacy scripts, or cross-entrypoint policy enforcement.

Public React Workflow Studio now places EVIE Safe Entry at the **top**, promotes the safe commands in Governed Flow and Completion Ledger guides, and labels the older direct R14/R15 flow explicitly as a less-protected compatibility path.

## Tests and honest limits

`pytest -q tests/test_safe_entry.py` covers policy inventory, explicit non-enforcement claims, parser denial of unknown run/module/publish flags, no-run without confirmation, real original hooks and distribution results, signed lease and local completion audit, stale/duplicate resume denial and strict no-final-DONE states.

The general Python release gate tests the wrapper with mock Docker but actual original generators. The separate R17 Offline Docker GitHub Action now **also runs the safe-entry end-to-end test with real isolated Docker for both stages**. A mocked test is not proof of sandboxing.

The CLI itself does not create new trust or enforce host permission boundaries. A malicious host, compromised signing key or reset nonce ledger can bypass local checks. Source inventory is limited, and signed local events are still not authenticated host telemetry. The path to stronger guarantees is a separately authorized migration to a single OS-protected execution service after backward compatibility, threat modeling and explicit consent.
