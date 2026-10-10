# Security Policy

EVIE combines local files, AI providers, publishing integrations, local bridges, and generated artifacts. Treat those boundaries explicitly.

## Credentials

Keep all real keys and OAuth tokens in local environment configuration or an appropriate secret store.

Never commit live:

- EV_API_KEY
- EV_OPENAI_API_KEY
- EV_ANTHROPIC_API_KEY
- EV_ELEVENLABS_API_KEY
- EV_GUMROAD_ACCESS_TOKEN
- EV_YOUTUBE_ACCESS_TOKEN
- provider secrets, cookies, or private keys

The repository's `.env.example` contains placeholders only.

## Runtime data

The public source distribution must not contain Vault contents, SQLite databases, SQLite WAL/SHM files, embedding indexes, generated private artifacts, logs, or backups.

## Publishing

Publishing modules should remain export-first / dry-run by default when possible.

A configured credential is not, by itself, evidence that a user intended a live publish operation.

Modern PhiOS integration should route live external effects through explicit Action Gate grants.

## Local EXE bridge

The Visual FX bridge can optionally launch configured local executables.

Treat executable paths and handoff directories as local configuration, not source-controlled data. Automatic execution should not be enabled merely because an executable exists.

## Public deployment

EVIE was designed local-first. Before exposing the API or dashboard to untrusted networks, review authentication, reverse-proxy/TLS configuration, allowed origins/hosts, upload limits, provider credentials, and any modules capable of external effects.


## Rung 5 local defaults

The API and Streamlit developer launchers bind 127.0.0.1; Docker Compose publishes ports on host 127.0.0.1 and requires a configured API secret. Protected endpoints refuse blank or known example keys. Do not expose this runtime outside the host without authentication/CORS/TLS threat modeling and review of all effectful modules. GitHub Pages never hosts the private runtime.


## R8 local signer trust

Keep all private signing keys on your own machine, encrypted with a passphrase and ideally outside the Git checkout. A trusted public key must be pinned independently; key fingerprints stated inside an attestation are only claims until verified against that trust root. Signed evidence does not imply runtime isolation, correctness, permission to publish or authority to run external tools. The subprocess used in R7 is still not an OS sandbox.


## R8B review proposals are never execution leases

`evie.family-handoff-proposal/1` is a digest-bound human-inspection request, with `requestedEffects: []`, `executionAuthorized: false` and `transportEnabled: false`. A separately signed `evie.family-handoff-acknowledgement/1` records the signing key holder's acknowledgement only; it does not guarantee recipient receipt, physical human identity, one-time consumption or permission to run tools. Trust roots must be independently selected, not taken from envelopes. All six proposed target transports remain disabled; no family app must treat these records as automation permissions.


## R9: OpenBlue preflight is not authorization

The OpenBlue validator performs strict local read-only contract checks and binds artifact bytes to the R8B review envelope using SHA-256. No networking, writing, target mutation, or job execution is available. The envelope is unsigned and can be replaced along with the referenced artifact, so a preflight PASS does not authenticate origin or grant import permission. OpenBlue's separate human approval remains mandatory. This does not certify construction geometry or engineering correctness.


## R10 recipient parser replay limitations

The local OpenBlue conformance harness deliberately imports and executes source from the operator-selected OpenBlue git checkout. It checks an explicit revision pin and clean tracked parser files, but **does not isolate malicious code**; run it only against reviewed trustworthy source. The source revision/digest and unsigned report do not authenticate an actual OpenBlue user's receipt or grant project import authority. The UI still requires explicit approval in OpenBlue, and EVIE adds no network transfer or agent execution.


## R11: FieldDeck action boundaries

EVIE Shelf cards and FieldDeck action IDs are separate authority domains. `evie.deck.draft/1` imports are never treated as executable FieldDeck steps. The new browser composer creates only manual selections from three fixed FieldDeck diagnostic IDs, with `policy.execution=denied` and independent review/authentication required. FieldDeck's own IssueOps and execution policy are unaffected. Parser compatibility testing on a reviewed pinned FieldDeck revision is not execution authorization.


## R12 workflow planning does not grant run authority

The new source-only Workflow Studio and `app.workflows.preflight` CLI never invoke the legacy runner, call `queries.create_run`, run a module, test a provider or grant a job lease. Optional flags affect only a proposed plan and default off. The source digest is a version comparison aid, not an authentication credential. All step decisions remain `candidate_only` or `skipped_by_default` with `executionAuthorized:false`. Name-heuristic effect warnings are incomplete and do not replace manual review. An independent execution security and budget gate is mandatory before making workflows runnable.


## R13 fixed supervised CAD local run

A user must explicitly invoke the R13 CLI with `--confirm-local-execution`, specifying a NEW staging directory outside the public checkout. Only the audited single-step OpenBlue concept workflow can execute; no API, DB, generic workflow runner, agent, model or publish action is used. A temporary Python subprocess with a minimal environment/timeout is **NOT a network or filesystem sandbox**. Local staged outputs and unsigned receipts should not be committed or treated as recipient approval or authenticated execution evidence. The browser performs local hash/geometry/source inspection only. The only actual permission is to run the one fixed local fixture; any downstream action remains denied.


## R14 supervised content review

Only manually approved one-step `local_content_hooks_review` can be invoked by the new CLI, with a short script and bounded output. The runner invokes the real v2 HooksGenerator with fixed output routing to a disposable workspace, an environment allowlist and a timeout. The subprocess is **not** an OS/network sandbox and output hooks are unverified editorial templates that may contain exaggerated claims. Review before publishing. The unsigned local receipt and matching browser display are **not** authenticated proof or permission to execute another module.
