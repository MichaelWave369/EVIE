# Contributing to EVIE

Thank you for contributing to EVIE.

## License

Project-owned code and documentation in the clean Commons release are MIT-licensed unless otherwise noted.

By submitting a contribution for inclusion, you represent that you have the right to submit it and agree that it may be distributed under the repository license.

## Never commit runtime/private data

Do not commit:

- `.env` files or live credentials;
- SQLite databases or sidecar files;
- Vault contents;
- generated embeddings/indexes;
- generated artifacts containing private material;
- logs or backups;
- OAuth tokens;
- model weights;
- exported user datasets;
- local EXE paths that expose private filesystem information.

Use `.env.example` with placeholders for configuration examples.

## Capability and authority

New modules may describe or expose capabilities, but integrations that publish, upload, mutate external systems, launch programs, or write outside bounded artifact paths should be designed for explicit authority gates and auditable receipts.

## Testing

Run:

```bash
python -m pytest -q
```

and the readiness/smoke tools where appropriate.
