# EVIE Public Release Plan

## Important

**Do not make the historical `MichaelWave369/EVIE` repository public in-place.**

That private repository contains runtime-derived files in Git history. The public Commons distribution should start from a clean source snapshot with no inherited Git history.

## Recommended publication path

1. Keep the historical repository private.
2. Optionally rename it to something like `EVIE-private-archive`.
3. Use the CI-produced `evie-commons-v0.1.zip` artifact from the `commons/export-v0.1` branch.
4. Create a new public repository, ideally `EVIE` or `EVIE-Commons`.
5. Initialize a fresh Git history from the extracted clean source.
6. Confirm the new repository is MIT-licensed and passes its public-release workflow.
7. Only then mark the new repository public.

## Clean-tree exclusions

The Commons export excludes:

- historical Git metadata;
- `data/` runtime artifacts and indexes;
- SQLite sidecars;
- private/generated Vault material;
- the personalized historical monetization guide.

The original private archive retains those materials for provenance.

## Publication gate

The clean release must pass:

- Python compilation;
- dependency installation;
- tests;
- JSON/config validation;
- tracked-file hygiene;
- MIT license presence;
- clean source archive generation.
