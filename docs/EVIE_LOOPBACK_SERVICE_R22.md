# EVIE R22: Local Read-Only Loopback Service Prototype

## Why only a read-only control plane?

R21 established `python -m tools.evie_safe` as the recommended human-run CLI, with signed, bounded, manually approved content work in the existing offline Docker capsules. R22 does **not** turn that into a remote command server. This rung introduces a small, authenticated, **read-only HTTP boundary** so we can test localhost restrictions, authentication, input allowlists, cross-origin rejection and auditability BEFORE exposing any execution action over a transport.

**The service has NO execution endpoints**. It never starts HooksGenerator, signs a lease, consumes a nonce, runs Docker, publishes, accepts a path to private data, or reads arbitrary session files. Existing Python CLIs remain separately callable on the host and are NOT restricted by this service.

## Operator steps (Windows PowerShell or Unix terminal)

From a trusted EVIE checkout:

Create a fresh locally stored bearer token in a new path **outside the repository**:

    python -m tools.evie_local_service token --token-file ../evie-local-service.token

This creates a random 256-bit hex token with exclusive file creation. On Unix-like hosts permissions are owner-only (0600) and the reader rejects group/world-accessible token files. On Windows, the file's actual access restriction depends on user and filesystem ACLs; **no Unix chmod security claim applies on Windows**. Keep the token private, off Git and out of screenshots or chat.

Start the listener in a trusted terminal (no hidden daemon, no background task):

    python -m tools.evie_local_service serve --token-file ../evie-local-service.token --port 8765

The server binds **only** to IPv4 `127.0.0.1`; no option exists to bind to 0.0.0.0, a LAN address, a public interface or a remote host. Ctrl+C stops the listener. Use a different numeric port as needed; `serve --port 0` requests an automatically chosen ephemeral local port printed to the local terminal, but token contents are never printed.

In a second terminal run an authenticated, localhost-only CLI probe:

    python -m tools.evie_local_service probe --token-file ../evie-local-service.token --port 8765

`probe` reads only the three hardcoded GET routes using a local bearer header. It does not write files, access runtime secrets, or start work. The service uses the standard Python library and does not require opening a browser or uploading anything.

## Exact HTTP routes

| Route | Result |
|---|---|
| `GET /v1/health` | Readiness and explicitly false execution/publishing authority |
| `GET /v1/policy` | R21 source-only policy and six known CLI entrypoint inventory; no host runtime probe |
| `GET /v1/plan` | R19 source-only two-stage plan marked not executed |
| `GET /v1/start`, `GET /v1/resume`, `GET /v1/audit` | 404. Not provided |
| `POST`, `PUT`, `PATCH`, `DELETE`, `HEAD`, `OPTIONS`, `TRACE`, `CONNECT` | 405. All non-GET operations denied |

Every allowed route requires the **exact** `Host: 127.0.0.1:<port>` and `Authorization: Bearer <token>` headers. Wrong/missing secrets are denied. Requests containing `Origin` or `Referer` are denied even with the token. The service returns no `Access-Control-Allow-Origin`, refuses URL parameters/unrecognized routes, sends no-store and nosniff headers, suppresses request logging, limits response size and reads no request body. The dedicated `probe` uses no HTTP proxy.

## Security truth table

- Possession of the local bearer token is **not independently authenticated OS user identity**; any process with file access to it may read these source-only routes.
- The HTTP connection is **not TLS encrypted**. It is strictly IPv4 loopback; do not tunnel, port-forward or proxy it outside the computer.
- Host and Origin restrictions reduce cross-site request abuse, but localhost and bearer tokens do **not** make a machine safe against compromised local processes, browser extensions or host-level attackers.
- The token remains valid until the service stops or the operator rotates the token file. There is no expiration, session revocation service, mutual TLS or durable audit trail in this prototype.
- No host execution is exposed, and there is no ability to submit scripts, select modules, issue signing keys, access local session contents, post to social platforms, spend funds, or invoke Docker.
- R13–R17 compatibility CLIs and the R19/R21 governed execution CLI remain directly callable on the machine; this service is NOT a mandatory policy enforcement layer or OS security boundary.
- The public GitHub Pages site only displays the guide. It NEVER contacts localhost automatically and cannot access this local service.

## Validation

`pytest -q tests/test_local_service.py` exercises real bound HTTP requests against an ephemeral `127.0.0.1` test server. It checks allowed requests, missing/wrong token, injected Host and Origin/Referer, denied verbs, query/path probes, non-overwriting private token files, symlinks/permissions, the CLI probe, and the absence of `start`/`resume` dispatch. It runs in the standard Python release gate and the dedicated Docker security gate (although service tests themselves do not launch containers).

## Promotion requirements for a future execution service

Before adding any POST-to-execute capability, qualify a distinct OS identity and filesystem/service privilege boundary, protected local state and audit receipts, strict allowlisted request formats with a CSRF story, independent approval/key handling, executor process supervision, Docker isolation for both stages, bounded memory/time, replay resistance and a migration plan for unrestricted old entrypoints. Until then HTTP execution remains **absent** by design.


## R23 addendum

R23 adds a **fourth** authenticated, read-only `GET /v1/security` route, reporting the always-closed execution-service promotion contract. The original R22 routes and refusal rules remain unchanged. See `docs/EVIE_EXECUTION_SECURITY_R23.md`. All HTTP execution methods remain denied.
