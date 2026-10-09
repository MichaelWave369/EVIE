# Full Sovereign Shelf · Nested Public Catalog (Rung 4)

This is a recovered **public projection**, not an executable engine or replacement for the private Sovereign Shelf source.

## Provenance
The original 2026 EVIE Sovereign Shelf registry, version 1.1.0, was recovered from the project owner's file library as EVIE_SOVEREIGN_SHELF_CARD_REGISTRY_v1_1_FIXED.json.
Source SHA-256: efe80d7172edce3db026b5160c2fa9bd41468c16b083b3d747ce96de1b485f35.
159 unique cards, 9 pack entries, 7 card classes. The reduced JSON committed at app/shelf/public_nested_catalog.json includes card names, categories, contracts, compatibility links and historical sequences. It omits pricing, revenue covenant, art prompt metadata, and other unnecessary source fields. This public extract is curated and versioned; the original source is NOT added to the public repository.

## Nested Explorer
The React frontend now offers **Full Shelf** navigation: All Access → pack → class/category → card → compatible/recommended cards. Ritual and mandate cards also expose their historical sequence as linked steps. Historical outputs are *claims recorded in the original specification*, not current deliverables.

## Deck Lab
Visitors can add up to 32 cards, reorder and remove them, view dependency gap hints, and export an evie.deck.draft/1 JSON. It is **design-only**: no executor, remote dispatch, API calls, model inference, or writes to EVIE. Missing contracts are informational. Agent or human deployment requires a separate governed local connector and review.

## Runtime truth
The only bounded CAD adapter is historical shard_floor_plan_generator → newly implemented openblueprint_floor_plan module, which outputs a concept JSON proposal and digest. It does NOT satisfy the original historical structure_spec → DXF/SVG contract. All other recovered cards are catalog_only, even when a similarly named EVIE module exists; registry presence alone is not verified execution.

## Safety
The public GitHub Pages site contains zero API credentials, no vault, no personal stored data, and does not contact localhost or EVIE's privileged backend.

## Rebuild
cd web && npm ci && npm test && npm run build
The web/scripts/sync-shelf.mjs script copies and validates the reviewed catalog at build time. Python tests validate the curated data and audit status.
