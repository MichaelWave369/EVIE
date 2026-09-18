# EVIE Public Release

EVIE is now published as a clean **Phi Commons** repository at:

```text
MichaelWave369/EVIE
```

The public repository was intentionally created with a fresh Git history.

## Private historical archive

The original development repository remains private at:

```text
MichaelWave369/EVIE-private-archive
```

Its historical source snapshot used for the Commons export was:

```text
63b589ffff034e09d1cdaca1889fd8dc98e4fb69
```

The private archive contains historical runtime-derived files and is **not** the repository that should be made public.

## Clean-source boundary

The public EVIE tree was seeded from the verified clean Commons export and excludes:

- historical private Git metadata;
- Vault/runtime database files and SQLite sidecars;
- generated embedding/index files;
- generated/private artifacts;
- the personalized historical monetization guide;
- live credentials and local environment files.

The public history begins only with clean Commons material.

## Public release gate

Every pull request and supported release branch should pass:

- dependency installation;
- Python compilation;
- JSON/config validation;
- the EVIE test suite;
- tracked-file hygiene;
- MIT license verification;
- clean source-archive generation.

## Provenance rule

The private archive remains the source of historical provenance.

The public repository is the supported Commons distribution.

No future release should merge the private archive's Git history into the public repository.
