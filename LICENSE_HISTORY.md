# EVIE License and Release History

## Private development era

The original EVIE repository was developed privately and contains historical runtime-derived files in its Git history.

That repository should remain private as the archaeological/source archive.

The source snapshot used to begin the Commons export came from:

```text
63b589ffff034e09d1cdaca1889fd8dc98e4fb69
```

The private history is intentionally **not** part of the public Commons distribution.

## Phi Commons clean release

Public EVIE releases should be created from a clean source snapshot that excludes private Git history and runtime state.

The Commons distribution uses the MIT License for project-owned code and documentation unless otherwise noted.

Third-party packages, external services, model weights, datasets, generated user data, and separately licensed assets remain under their respective terms.

## Why the history is separated

Licensing history and data provenance are not the same thing.

The private repository has tracked runtime artifacts such as SQLite sidecar/index files. Even where a particular file appears harmless, the project does not treat old runtime history as suitable for public release without a full forensic review.

The safe default is therefore:

```text
private historical repository
        ↓
clean source snapshot
        ↓
public Commons repository
```
