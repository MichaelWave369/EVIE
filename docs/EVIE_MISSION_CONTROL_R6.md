# EVIE Capability Mission Control · Rung 6

## What this is

A **static, source-derived** inventory of EVIE's current Python capability registry and configured workflow definitions. This is a bridge between the revived backend and the public React frontend, not a browser-accessible control surface for private API operations.

Build-time evidence comes from:
- `app/modules/__init__.py`: module keys and class names instantiated in REGISTRY
- `configs/workflows.json`: configured workflows and referenced module/workflow edges

The deterministic exporter `web/scripts/mission-audit.mjs` parses these two checked-in files, validates unique names and dependencies, detects nested-workflow cycles, and emits the JSON for the React frontend. Vite runs the exporter via `web/scripts/sync-shelf.mjs` before every dev/test/build.

The snapshot includes a SHA-256 digest of its exact sources. It contains no runtime credentials, private vault contents, provider requests, or local host information.

## Evidence tiers

- **Registered only:** a module name is visible in EVIE's Python REGISTRY. No test result, provider readiness, safe operation, or functional quality is implied.
- **Targeted test source:** a focused smoke/regression test is checked into the repository for the bounded OpenBlueprint CAD producer. This is *test-source evidence*, NOT a claim that the capability is available on the viewer's machine or that a real CAD workflow was validated end to end.
- **Live-qualified: zero reported.** A static GitHub Pages site cannot inspect a local person's runtime. A future opt-in receipt importer or local-only bridge will be required before updating this category.

**117 registered modules, 10 configured workflows** is the inventory at PR creation. The build generator recalculates counts whenever code changes. Module registrations and historic 159 Shelf card definitions are separate namespaces and must never be combined as a runnable feature total.

## Mission Control UX

- Search and group Python module registrations
- Filter by participation in workflows, code-level test-source evidence, and possible external-effect name heuristic
- Inspect a module's Python class, registry identity and directly referencing workflows
- Inspect ordered workflow steps, optional edges, nested workflow references and missing dependencies
- Navigate between modules and workflow details
- Copy the explicit, local-only doctor command: `python -m tools.evie_doctor --json --smoke-cad`

No buttons here dispatch jobs, upload data or make authenticated API requests.

## Governance

Heuristic external-effect flags (publishing, launch, bridge, provider names) are conservative hints for code review, **not** a security analysis or an authorization mechanism.

Use the local Doctor for configuration wiring and its optional *single* deterministic disposable CAD smoke. Other modules need separately designed, opt-in tests that stage outputs in temporary directories and enforce budgets, side-effect controls, receipts and human review.

**Never add EV_API_KEY, OAuth tokens, personal source files or generated private artifacts to the public snapshot.** The Pages deploy remains static. Real agent execution must stay on the localhost backend until a separately reviewed connector and action gate are implemented.

## Tests

- `cd web && npm ci && npm test && npm run build` verifies generated manifest source linkage, unique module keys, workflow graph validation, truthful evidence and no secrets.
- The EVIE Public Release Gate still runs full Python tests and public-tree hygiene on the same PR.
- Pages workflow triggers are extended to source changes in the module registry and workflow JSON.
