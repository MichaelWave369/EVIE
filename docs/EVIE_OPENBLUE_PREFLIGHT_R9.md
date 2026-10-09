# R9: EVIE → OpenBlue artifact preflight (read-only)

**Boundary:** This feature is implemented in EVIE only. OpenBlue is managed in a separate repository/session. It does not modify OpenBlue, upload files, connect to an OpenBlue API, or approve a CAD import.

## Grounded OpenBlue importer contract
Reviewed against `MichaelWave369/OpenBlueprintStudio` main at commit `015845851191b21764da435ac05f45ccc3779d7b`, particularly `src/evieBridge.js` and `src/model.js`.
Supported artifact: `openblueprint.evie-proposal/1`; nested project: `openblueprint.project/1`; source declaration `system=EVIE` plus `cardId`, `runId`, `mode=fixture|generated`.
Max 5,000,000 bytes of JSON; max 400 walls + symbols; unique IDs; finite coordinates, bounded heights/thicknesses; supported symbol types and units.
EVIE's validator is deliberately more conservative about malformed JSON and control characters. Passing this check is **not a guarantee** that any future OpenBlue importer will accept the file.

## Python CLI (no network, no output files)
1. Produce or choose your OpenBlueprint proposal JSON locally.
2. Create an R8B review envelope with `python -m tools.evie_family_gate prepare --target openblue --kind openblueprint.evie-proposal/1 --artifact ./plan.json --proposal ./review.proposal.json`.
3. Run `python -m tools.evie_family_gate inspect-openblue --proposal ./review.proposal.json --artifact ./plan.json`.
4. Review the output; **manually** open OpenBlue and import via its existing EVIE CAD preview/approval UI. No project mutation occurs in EVIE.

The report binds exact artifact bytes (SHA-256 and byte length) to the review envelope, verifies its expiry/target/no-effects flags, and inspects the nested plan geometry. It excludes full plan contents and private filesystem paths; no reports are written unless you independently save stdout.

## React browser inspector
Inside EVIE Family Gate, upload/select the *two local files* (R8B review envelope JSON and OpenBlue proposal JSON) to check the same structural contract, byte length, digest and expiry entirely inside your browser. The files are not uploaded to GitHub Pages and the site never communicates with localhost.

## Governance
The review envelope is **unsigned**; a malicious actor can forge both envelope and matching artifact hash. R8B's optional signed acknowledgement is separate and does not prove recipient acceptance or grant permission.
This R9 feature does not validate building codes, layout accessibility, structural safety, spatial collision or production CAD quality. No receipt from OpenBlue exists, and no end-to-end recipient import/approval test is claimed.
All family transports remain disabled. The only actual handoff is the previously existing manual local file import in OpenBlue.

## Tests
`pytest -q tests/test_openblue_family_preflight.py` plus the full EVIE release gate and the EVIE React Vitest/production build.
