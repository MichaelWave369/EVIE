# Phi Commons — EVIE

EVIE is part of the **Phi Commons**.

Unless a file or directory states otherwise, original EVIE software and documentation in the clean Commons release are provided under the MIT License.

## Why EVIE belongs in the Commons

EVIE contains an early implementation of a pattern that later became central to PhiOS:

```text
Vault → Modules → Workflows → Artifacts
```

The project also contains reusable work around:

- modular capability registries;
- workflow orchestration;
- RAG and local knowledge storage;
- readiness/smoke validation;
- export-first publishing;
- graceful partial/degraded completion;
- local image generation;
- local EXE handoff bridges;
- scheduler/factory patterns;
- artifact packaging and traceability.

## Historical commercial mission

EVIE was originally designed as a content/productization and income engine.

The Phi Commons release does not erase that history. It simply changes the default posture from:

```text
CAPABILITY → PACKAGE → SELL
```

toward:

```text
CAPABILITY → PACKAGE → SHARE → MODIFY → BUILD
```

Publishing and storefront modules remain useful examples and optional capabilities.

## Capability is not authority

Several EVIE modules can publish, upload, launch external tools, write files, or call network services.

Open licensing does not authorize those actions.

When EVIE concepts are integrated into modern PhiOS, mutating or externally visible operations should sit behind explicit Action Gate grants and produce receipts.

## Donor-system rule

EVIE is preserved as a donor system, not a mandatory runtime dependency of PhiOS.

Useful components may be adapted, absorbed, or rewritten behind modern PhiOS contracts without preserving every historical API.
