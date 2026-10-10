# EVIE R19: Offline Docker Capsules for Both Governed Content Stages

## What changes

R18's `python -m tools.evie_governed_flow start` previously generated hooks through a credential-stripped host Python subprocess. In R19 that **controller start command requires a locally available Docker Engine/Desktop and an already installed trusted `python:3.11-slim` image**. Missing Docker or missing image refuses **before** creating a session. The original R14 standalone `tools.evie_supervised_hooks` remains for compatibility but is correctly identified as **legacy host-subprocess execution**, not isolated.

R19 adds a fixed minimal capsule for the existing actual `app.modules_v2.hooks_generator.HooksGenerator` and its original worker. Only four public source files plus small package markers are exposed inside the Docker container:

- `app/modules/base.py` (base class only; the full `app/modules/__init__.py` registry is NOT copied)
- `app/modules_v2/base.py`
- `app/modules_v2/hooks_generator.py`
- `tools/evie_hooks_worker.py`

The container receives the bounded operator script through stdin, writes only to private `/tmp`, returns a capped JSON response through stdout and is independently checked using the existing R14 artifact shape, nine-hook category validation, source SHA-256 and input digest. No private checkout, database, .env, other registered modules or provider credential is mounted.

## Docker hardening

The hooks capsule reuses the R17 audited invocation policy: `--pull=never`, pinned inspected local image ID, `-i`, `--network=none`, read-only root and source mount, `--cap-drop=ALL`, `--security-opt=no-new-privileges`, unprivileged UID/GID, no IPC, memory/CPU/PID limits and 16 MiB private tmpfs. No host-Python fallback is permitted by the governed start command. It cannot protect against a malicious Docker daemon, a compromised host, filesystem changes by privileged local users, or kernel vulnerabilities.

The R14 output receipt gains `executionIsolation` metadata when the runner is used through the governed controller. The 01-hooks-paused event also records `stageOneOSIsolated:true` and the claimed local Docker profile. **These are unsigned local observations**, not independently authenticated host attestations or proof against an attacker who controls the host.

## Operator commands

Before starting, explicitly install/start Docker Desktop/Engine and preload the image yourself (EVIE does not pull images for you):

    docker pull python:3.11-slim

Create an original script `draft.txt`, then:

    python -m tools.evie_governed_flow plan
    python -m tools.evie_governed_flow start --session-dir ../evie-flow-session-001 --script-file ./draft.txt --topic "EVIE Creator Loop" --confirm-local-execution

The controller stages nine hooks, writes `01-hooks-paused.json`, and stops. Inspect and fact-check. `status` remains read-only:

    python -m tools.evie_governed_flow status --session-dir ../evie-flow-session-001

Independently sign the exact hooks artifact via R16's interactive encrypted Ed25519 key:

    python -m tools.evie_action_lease issue --hooks-dir ../evie-flow-session-001/hooks --approved-hooks-sha256 YOUR_REVIEWED_64_CHARACTER_SHA256 --stage-dir ../evie-flow-session-001/distribution --signing-key ../evie-lease-private.pem --lease-file ../evie-flow-lease-001.json

Then explicitly resume using the **second** offline container and a persistent local nonce ledger:

    python -m tools.evie_governed_flow resume --session-dir ../evie-flow-session-001 --lease-file ../evie-flow-lease-001.json --trusted-public ../evie-lease-trusted-public.pem --ledger ../evie-local-lease-ledger.sqlite --confirm-local-execution

Both actions are human-triggered. There is no background execution, automatic key signing, remote upload or publishing.

## Legacy lanes and migration

The following standalone commands still exist and **bypass parts of the stronger controller**, because removing or silently changing them would break prior working workflows:

- `tools.evie_supervised_hooks`: R14 direct host Python hook generator (not Docker).
- `tools.evie_supervised_distribution`: R15 second-stage host Python with explicit hash and confirmation but without signed lease.
- `tools.evie_approved_distribution`: R16 signed second stage and one-host nonce ledger, but host Python rather than Docker.
- `tools.evie_isolated_distribution`: R17 signed Docker second stage but no governed Stage 1.

**Preferred path for new two-stage runs is the R19 governed controller**, which requires Docker for both Stage 1 and Stage 2 and a fresh independent signed approval before Stage 2. Direct local programs with permission to run on the host cannot be forcibly blocked by Python-only code. Making this a mandatory service-wide policy is a later architectural change.

Old R18 sessions that were started using host Python remain inspectable with `status` but are deliberately **not eligible for R19 signed resume**. Begin a new R19 session to use the stronger isolation contract.

## Tests / evidentiary limits

The standard Python gate verifies minimal capsule file exposure, exact restricted invocation, input/credential denial, fail-closed when Docker is missing and no auto-retry. It uses mocks for Docker but real original Python producers; a mock does not prove container isolation.

The dedicated real-Docker GitHub gate now runs `tests/test_hooks_container.py` and the R18/R19 governed-flow test with `EVIE_TEST_DOCKER=1`, including a **real original HooksGenerator inside network-disabled Docker**, an independently signed lease, and **real DistributionGenerator inside a separate network-disabled Docker capsule**. That CI gate retains the external-network denial test. Check all three CI results (React, Python and Docker) before merging.

Nothing in R19 authorizes automated publishing, authenticated editorial claims, unreviewed model calls, budget spending, arbitrary modules, third-party acceptance or universally tamper-proof ledgers.
