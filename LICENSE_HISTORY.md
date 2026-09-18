# EVIE License and Release History

## Private development era

EVIE was originally developed in a private repository.

That historical repository is preserved at:

```text
MichaelWave369/EVIE-private-archive
```

The source snapshot used to create the first clean Commons export was:

```text
63b589ffff034e09d1cdaca1889fd8dc98e4fb69
```

The private archive contains historical runtime-derived files and remains private for provenance and safety.

## Phi Commons public era

The public Commons repository is:

```text
MichaelWave369/EVIE
```

It was created with a fresh Git history from a verified clean source export. The private repository's Git history was intentionally not imported.

Project-owned EVIE code and documentation in the public repository are released under the MIT License unless otherwise noted.

Third-party packages, external services, model weights, datasets, generated user data, and separately licensed assets remain under their respective terms.

## Why the histories are separated

Licensing history and data provenance are not the same thing.

The historical repository contained tracked runtime-derived files such as SQLite sidecar/index artifacts. Even where an individual file appears harmless, old runtime history is not treated as suitable for public release without full forensic review.

The permanent boundary is therefore:

```text
private historical archive
        ↓
verified clean export
        ↓
public Phi Commons repository
```

The public repository should never absorb the private archive's Git history.
