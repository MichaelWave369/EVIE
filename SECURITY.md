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
