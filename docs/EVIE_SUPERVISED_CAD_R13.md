# EVIE R13 · Supervised Single-Step CAD Workflow Run

## What really executes
R13 is the first explicitly opted-in **local execution** of the checked-in `openblueprint_concept_floor_plan` workflow's single known `openblueprint_floor_plan` step. It directly calls the real `OpenBlueprintFloorPlanModule.generate` method in a disposable Python subprocess, not the legacy `app.workflows.runner.run_workflow` (which writes database records). This runner accepts NO other workflow, no topic string, no arbitrary constraints and no general module IDs.

## Local operator command
Run from your own trusted EVIE Git checkout:

    python -m tools.evie_supervised run openblueprint_concept_floor_plan --stage-dir ../evie-cad-review-001 --confirm-local-execution

Choose a **new** stage directory each time, outside the repository. The command refuses an existing folder, an unknown workflow and runs missing the explicit `--confirm-local-execution`. For an invalid run it exits nonzero and creates no staged review bundle.

## Fixed scenario, budgets and artifacts
The fixture is a 24 × 16 ft concept room with five walls including a midpoint vertical partition, one door marker, one network marker, fixed title and local-only output. It uses no API providers, prompts, secrets or models. The subprocess uses Python `-I`, a fresh temporary work directory, restricted environment allowlist, discarded stderr and an explicit **20-second** timeout. Output is bounded to 64,000 bytes; the whole review bundle is capped at 128,000 bytes.

Before running, the operator CLI performs the R12 source-only preflight and checks the workflow still contains exactly one `openblueprint_floor_plan` step, no publishing dependencies or extra steps. It rechecks source digests after the worker completes and rejects changes. The worker generates a real versioned OpenBlue proposal and original digest receipt. The parent independently validates exact geometry, symbols, source labels and SHA-256 before staging.

After passing, the CLI creates a new folder with exactly:
- `openblueprint.evie-proposal.json`: real generated CAD proposal bytes.
- `workflow-preflight.json`: original R12 source-only plan, still marked as unexecuted planning data.
- `review-receipt.json`: unsigned `evie.supervised-cad-review/1` local execution observation bound to workflow source, producer source and artifact hashes.

## Operator-controlled review
Open EVIE React → Mission Control → Workflow Studio → `openblueprint_concept_floor_plan` → Supervised CAD Run. Select the staged receipt and proposal files. EVIE compares SHA-256, source revision, fixed geometry and permission declarations entirely in the browser. Neither file is uploaded. After inspection, independently open OpenBlue Studio and use its existing import/preview/Approve controls. **The browser never runs Python or imports the file for you.**

## Critical security boundaries
- This runner intentionally executes a fixed audited local module, with an **explicit CLI confirmation**, but the Python subprocess is NOT an operating-system isolation boundary. Network access and host filesystem permissions are not constrained by OS policy. Run only a trusted source checkout.
- The one local fixture run is not a global workflow-execution grant. In receipts, `localFixtureExecuted=true` describes the observed local run; `downstreamActionAuthorized=false` prevents promoting the receipt into later permissions.
- A locally produced unsigned receipt can be forged and does not prove host integrity. It does not authenticate a user, recipient acceptance, or a third-party audit.
- OpenBlue is not invoked. The staged CAD artifact has no construction safety certification, verified code compliance, or guaranteed real-world dimensions.
- R12's plan remains marked `executed=false`, because it is a static plan snapshot. The separate R13 observation records the actual local fixed run.
- All other 9 workflows, publisher modules, network endpoints and agent permissions remain unchanged and disabled by R13.

## Tests
`pytest -q tests/test_supervised_cad.py` covers a real worker execution, three staged artifacts, provenance and digest checks, rejection of other workflows, no overwrites, fixed spec drift, tampered output, and environment credential filtering. React `supervisedReview.test.js` covers match, tamper, wrong source and forged authority. Both suites run as part of EVIE's usual release and Pages gates.

## Next
R14 can add a signed and independently replayed local workflow observation, or another explicitly reviewed deterministic media/content step. Do not generalize the executor until stronger isolation and time/budget/approval policies are in place.
