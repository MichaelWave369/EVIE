# EVIE R12: Real Workflow Revival Studio (source-only preflight)

## Why this rung exists
EVIE has ten configured workflows combining historical business, vault, publishing, media, CAD and nested flow steps. Its existing `run_workflow(name, dry_run=True)` creates a database run record before returning module-availability checks. R12 adds a **separate source-only planner** that does not call that runner, instantiate modules, touch the DB, call models or execute a job.

## React Workflow Studio
Open EVIE public site → Mission Control → Workflow Studio. Select a real registered workflow, inspect expanded nested workflow steps, and simulate its optional `when_constraint` flags. Flags are **simulation inputs only**, not authorizations. All module steps are shown as `candidate_only` or `skipped_by_default`; neither state executes code.

The React build reads the real `configs/workflows.json` and `app/modules/__init__.py`, including each step's `when_constraint`. It annotates each workflow with the registry source digest and names any potential effects using a **module-name heuristic**, which is not a security audit.

Export JSON uses `evie.workflow-preflight/1`, listing selected conditions, source SHA-256, planned/skipped steps, nested expansion and explicit `executionAuthorized:false`, `executed:false`, `databaseTouched:false`, `providerAvailabilityVerified:false`.

## Local Python CLI: no database or runtime
From the EVIE repository root, with only Python standard library available:

    python -m app.workflows.preflight --workflow openblueprint_concept_floor_plan
    python -m app.workflows.preflight --workflow vault_to_lesson_pack --enable include_audio
    python -m app.workflows.preflight --workflow trend_to_money_publish --enable run_publish_workflow

That last command **does not publish**. It merely expands the optional subworkflow for review and flags possible publishing modules. No API credentials are needed. No data directory is created. Unknown flags are rejected; optional branches are off by default.

## Governance, safety and limitations
- Maximum 128 plan rows and 12 nested workflow levels; nested cycles are rejected.
- Only flag names found in the source-defined workflow (including reachable nested workflows) can be enabled for planning. Unrecognized flags and duplicate flags are rejected.
- All output steps explicitly say `executionAuthorized:false` and `executed:false`. There is no public execution endpoint, remote job submission, authentication grant, local daemon, token spending, publishing call or database run record.
- `candidate_only` means included for further review; it DOES NOT mean runnable or qualified. Registered modules can still lack local dependencies, API connectivity or safe output handling.
- Some workflow steps (e.g., publish controller) may be effectful even if constraints appear disabled. Naming-based risk warnings are incomplete. A separate effect/side-effect inventory is required before any executor is exposed.
- The workflow manifest describes code at the published revision, not a current local model/environment inventory.

## Why not simply call the old dry_run endpoint?
The legacy implementation creates a `queries.create_run` record before its `dry_run` branch. Its `ok` checks mean only that module names exist in the registry. It is unsuitable as evidence of a pure, no-write dry run.

## Tests
`pytest -q tests/test_workflow_preflight.py` exercises real workflows, optional branches, nested expansion, injection-resistant flags, and verifies separation from the legacy runner and DB imports.
`cd web && npm test && npm run build` exercises equivalent browser planning, source digest and no-execution invariants.

## Next R13
Audit and qualify a first actual workflow that can run end to end under explicit local-only, temporary-output, budgeted, supervised conditions. Start with the single-step OpenBlueprint concept workflow, then expand to deterministic content transforms after testing dependencies. No global workflow execution approval from this rung.
