# EVIE Sovereign Shelf Architecture Pack: Recovered Catalog (Rung 3)

Historical source: user-owned EVIE_SOVEREIGN_SHELF_CARD_REGISTRY_v1_1_FIXED.json, registry v1.1.0.
SHA-256 source bytes: efe80d7172edce3db026b5160c2fa9bd41468c16b083b3d747ce96de1b485f35.
Repository contains only a minimal architecture metadata extract from the 159-card source, not its full marketing/revenue records.

## Discovery
Authenticated GET /v1/shelf/architecture (all eleven cards and two ritual sequences).
Authenticated GET /v1/shelf/architecture/floor_plan_generator (single card, also accepts shard_floor_plan_generator).
No execution endpoint exists in this catalog. The existing EVIE module API handles actual execution.

## Execution truth
The historical Floor Plan Generator requires structure_spec and promises floor_plan_dxf and floor_plan_svg.
Neither its structure_spec input contract nor DXF/SVG outputs are implemented by the modern EVIE openblueprint_floor_plan module.
The new module is a bounded adapter that generates OpenBlueprint proposal JSON and a local SHA-256 digest for manual approval.
Other ten cards and both rituals remain catalog_only with no verified executors.
Do not claim CAD-ready floor plans, code compliance, structural checks, permit readiness, or authenticated origins.

## Future milestones
Implement a strongly validated structure_spec parser; bridge to a bounded CAD producer; test Python producer against OpenBlueprint JS consumer; add DXF/SVG only when independently verified and audited; keep human approval for mutation.

pytest -q tests/test_shelf_architecture.py