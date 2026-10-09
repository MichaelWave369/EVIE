# EVIE Commons → OpenBlueprint Studio CAD Producer (Rung 2)

New deterministic producer module: openblueprint_floor_plan.
These files are not evidence of restoration of the original Sovereign Shelf CAD cards.

Run via POST /v1/modules/openblueprint_floor_plan/generate with authorized EVIE API key.
Example JSON body:

    {"topic":"Workshop Concept","constraints":{"units":"ft","width":28,"depth":20,"partition":"vertical"}}

Or run the EVIE workflow openblueprint_concept_floor_plan with the same constraints.

EVIE creates openblueprint.evie-proposal.json and sha256-receipt.json in unique local artifact paths.
Download the proposal, open OpenBlueprint Studio, click EVIE CAD, inspect the read-only preview,
then explicitly approve or reject. Approval replaces the current plan; export a JSON backup first.
The SHA-256 receipt proves bytes, not authentic source identity or engineer approval.

Limits: concept-only rectangular perimeters, one optional partition, conceptual door/network markers.
No true wall cutouts, certified CAD geometry, BIM, code compliance, network routing, or automation authority.
All measurements require independent human verification.

Tests: pytest -q tests/test_openblueprint_floor_plan.py