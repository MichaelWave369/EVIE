# EVIE R17: Optional offline, minimal Docker source capsule

## Purpose

EVIE R16 supports a signed, exact-artifact, single-use lease for the **local distribution-draft** action. R17 adds an **opt-in** backend that runs the same real second-stage `DistributionGenerator` in a narrowly restricted Docker container rather than a host Python subprocess.

This is intentionally **not** a generic workflow orchestrator, service daemon or network executor. It does not automatically chain the R14 hooks stage, nor does it authorize posting, emails, sales-platform updates or any unrelated registry module.

## What gets mounted

The R17 launcher copies exactly four inspected/restricted source files from the current EVIE checkout to a private temporary capsule:

- `app/modules/base.py`
- `app/modules_v2/base.py`
- `app/modules_v2/distribution_generator.py`
- `tools/evie_distribution_worker.py`

Tiny `__init__.py` markers create importable packages. In particular, the real `app/modules/__init__.py` registry is **not copied**, because it imports dozens of unrelated modules. The container has **no access to the whole EVIE checkout**, its `.env`, databases, secrets, downloaded models, logs or source-control metadata.

The worker reads its reviewed nine-hook input from stdin. It writes the distribution draft within its private 16 MiB `/tmp` tmpfs. Only JSON response bytes are returned through stdout, and the original R15 parent independently validates the result, digest, exactly five consumed hooks and output limits before staging it on the host.

## Docker restrictions

The runner invokes a local installed Docker Engine or Docker Desktop with these hard settings:

- `--pull=never` and content-addressed local image ID obtained from `docker image inspect python:3.11-slim`
- `--network=none` to deny **external** network interfaces/routes
- `--read-only` container root, plus one read-only bind of only the minimal capsule
- `--user=65534:65534`, `--cap-drop=ALL`, `--security-opt=no-new-privileges`
- `--pids-limit=64`, `--cpus=1`, `--memory=256m`, `--memory-swap=256m`
- `--ipc=none`, `--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=16m,mode=1777`
- Python `-I` isolated import mode, fixed audited worker entrypoint, no interactive TTY or Docker socket mount

**Caveat:** Docker is OS/container isolation, not an absolute host security guarantee. The Docker daemon is privileged; Docker Desktop and container runtime flaws remain relevant. Docker `--network=none` is not a proof that every kind of IPC or loopback socket is impossible. The restriction applies to the container, not to host-side preparation, approval checks or the R14 stage-1 hooks generator.

## Operator instructions

1. Install/start your own trusted Docker Engine or Docker Desktop, which is **not installed or configured** by EVIE.
2. **Explicitly** preload and trust a Python 3.11 slim image. EVIE does not pull images on demand:

       docker pull python:3.11-slim

3. Use the **existing R14** supervised nine-hook workflow to create a review bundle; inspect and fact-check the nine hooks.
4. Use R16's `python -m tools.evie_action_lease issue` command to sign a fresh approval. The lease must bind your exact current R14 `artifactSha256`, workflow registry source digest, and a **brand-new R17 stage directory**. TTL is 5 minutes by default.
5. Instead of the earlier `tools.evie_approved_distribution` command, run:

       python -m tools.evie_isolated_distribution --hooks-dir ../evie-hooks-review-001 --approved-hooks-sha256 YOUR_REVIEWED_64_CHARACTER_SHA256 --stage-dir ../evie-distribution-review-001 --lease-file ../review.lease.json --trusted-public ../evie-lease-trusted-public.pem --ledger ../evie-local-lease-ledger.sqlite --confirm-local-execution

Use a fresh stage directory and approval for each attempt. Always reuse a single protected nonce-ledger file on your host. If Docker is absent or the image is missing, the command refuses to run **before** spending the lease. If the image is present but container execution fails after the lease is spent, the lease is burnt; do not silently retry. Review why it failed, choose a new stage destination, and issue a new lease.

## Review evidence and limits

The successful R17 execution stages the same R15 distribution draft, source-only plan, R15 unsigned draft receipt, and R16 `lease-consumption.json`. The R16 observation now also includes `containerIsolation` metadata identifying the locally inspected image SHA-256, Docker offline profile and configured restrictions. It is **not** a signed or independently verified host-attestation document.

The inherited R15 receipt's `networkSandboxEnforced:false` is its legacy static policy assertion and is **not upgraded** to an independently verified security claim by a new backend. To inspect which Docker profile was requested, use the separate R16 consumption observation. The browser's existing four-file editor/reviewer remains unchanged.

## Important nonclaims

- The R15 and R16 **host Python** CLIs still work. This is an **optional** stronger lane, not mandatory isolation for every EVIE action.
- The Docker daemon, source checkout and signing operator must be trusted. An adversary controlling them can circumvent local checks or forge unsigned observations.
- No cross-host ledger consensus exists. Single-use is enforced only among clients using the same intact SQLite ledger.
- A successful container run is a local compatibility/production observation, not a demonstration of publication, third-party acceptance or factually accurate marketing content.
- Docker support differs across machines. Running these commands on Windows may require Docker Desktop's Linux-container backend and permissions to bind a temporary directory.
- In-memory input/outputs are bounded, but the privileged host launcher is not itself OS-isolated.

## Tests

The standard Python gate runs `tests/test_container_isolation.py` in no-Docker mode: fixed policy flags, minimal source surface, missing Docker rejection before spending a lease, and mock backend routing into the existing authenticated local R15 path.

The new `EVIE R17 Offline Docker Capsule` GitHub Action **explicitly preloads** the image on the CI host, runs actual R14 source generation, validates/signed R16 approval, burns the nonce, and executes the **real** v2 distribution worker inside Docker. It additionally checks that an external connection attempt fails with `--network=none`. A green dedicated workflow is required alongside normal EVIE Python/React checks before merging.

## Next rung

Once this single action's isolation is proven repeatably on the host OS, consider an explicitly governed orchestration controller that requires per-stage signed leases and uses only an audited catalog of isolated workers. Do not broaden to all 117 registered modules or generic command execution without separate capability-by-capability qualification.
