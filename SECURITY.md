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
