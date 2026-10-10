# EVIE R23: Fail-Closed Execution-Service Security Contract

## Purpose

R22 created a token-protected 127.0.0.1 control plane with read-only health, source policy and workflow plan. R23 adds an **explicit readiness contract**, not an execution server. It intentionally reports an unqualified execution boundary until additional enforcement can be built, independently tested and reviewed.

Service endpoints are now exactly:

| Authenticated GET route | Result |
|---|---|
| `/v1/health` | Read-only service readiness |
| `/v1/policy` | Source-only legacy execution entrypoint inventory |
| `/v1/plan` | Unexecuted fixed two-stage plan |
| `/v1/security` | Source-bound, fail-closed execution promotion blockers |

**No `POST /v1/start`, `POST /v1/resume`, `POST /v1/execute` or publishing API exists.** Other verbs remain 405; unrecognized routes remain 404 when authenticated. `Origin`, `Referer`, invalid Host and missing token remain denied.

## How to inspect safely

From a trusted EVIE clone:

    python -m tools.evie_execution_security assess

This command reads a fixed set of six repository source files to bind the report to actual source SHA-256, and prints a JSON security contract. It does not create files, access the operator's token, read personal sessions or nonce ledger, launch Docker, consume leases, or modify runtime policy. There is no `--force`, `enable-execution` or promotion command.

An already running R22 local read-only service can be probed with the original authenticated CLI:

    python -m tools.evie_local_service probe --token-file ../evie-local-service.token --port 8765

The probe now verifies all FOUR read-only routes and explicitly checks the security report remains `executionAllowed:false` and `promotionReady:false`. Do not paste your bearer token into a browser or website. The GitHub Pages interface only displays local instructions and never calls your localhost.

## Six unresolved promotion requirements

| Mandatory condition | Current state |
|---|---|
| Per-request authenticated OS client principal | NOT IMPLEMENTED. A bearer token is only a secret; it cannot identify a local user/process |
| Least-privilege OS-separated execution broker | NOT IMPLEMENTED. R22's server cannot safely operate as one merely by opening routes |
| Protected, nonreplaceable approval and nonce store | NOT IMPLEMENTED. Current SQLite state can be replaced by a host-level user |
| Mandatory enforcement over older direct execution CLIs | NOT IMPLEMENTED. Existing R14/R15/R16 host-Python commands remain available |
| Atomic service-owned HTTP request, signed approval and worker binding | NOT IMPLEMENTED. R16 one-use leases apply to local CLI path/ledger |
| Independently trusted runtime evidence | NOT IMPLEMENTED. Existing stage and container-profile receipts are unsigned local observations |

The R19 dual-Docker worker restrictions and R16 Ed25519 local leases are tested controls for the **manual CLI**. They cannot be promoted to transport-level identity/permission guarantees without a separate trusted service and host isolation. A future rung must prove each requirement with independently grounded tests, not by changing six booleans to `true`.

## Defense against forged input

`deny_http_execution(intent=...)` refuses any untrusted HTTP execution proposal, including fabricated principals, 'root/admin' roles, valid-looking signed leases, runtime-receipt JSON and caller-supplied `allChecksPassed` fields. It has no path to worker dispatch, file writes, nonce spending or publishing. The actual HTTP handler still has **no execution route at all**; the contract doesn't consume request bodies and is not a substitute for future authentication.

## Token-file hardening

On POSIX, the R22 loader now also checks token file ownership matches the service process's effective user and rejects multiply hard-linked token files, in addition to its existing owner-only permission requirement. This is one local-file hygiene improvement, not an authenticated HTTP client identity protocol. On Windows, file ACL ownership and deny rules still need explicit Windows-specific verification and safe provisioning before any execution service.

## Validation and boundaries

`pytest -q tests/test_execution_security.py tests/test_local_service.py` checks exact fixed-source SHA-256, six closed requirements, forged approval/role negative controls, invalid-source refusal, no promotion CLI, four real localhost GET routes, continued rejection of mutating methods, forbidden browser origins, token hygiene and failure to access execution functions.

The dedicated `EVIE R17 Offline Docker Capsule` workflow still tests the genuine dual-Docker manual workflow as a regression gate; that test does **not** imply this HTTP control plane can launch workers.

### No false DONE

The R20 completion auditor remains the authority for a **narrow locally verified draft artifact** only. Neither that auditor nor this service report establishes independently authenticated execution, editorial acceptance, a published outcome, a final deliverable or permission for new jobs.

## Requirements before any execute route

Build a dedicated OS-privileged boundary separating untrusted transport from the worker; authenticate the connecting local principal; persist protected, atomic per-request replay state; enforce one service-controlled entrypoint after an explicit legacy migration; qualify Docker containment and failure recovery; establish independently trusted signed execution receipts and explicit user approval. Add mutating routes only in a separately reviewed PR with negative-control security tests. R23 does **none** of those things silently.


## R24 addendum: native OS observations, not promotion

R24 adds `python -m tools.evie_operator_state inspect` as a separate local read-only tool. It checks the process-to-file owner relationship and candidate file metadata on Windows and POSIX without reading private file contents or enabling service execution. The R23 security source inventory now binds this inspector file too. None of R23's six unmet promotion requirements are satisfied merely by R24's observation. Refer to `docs/EVIE_OPERATOR_STATE_R24.md`.
