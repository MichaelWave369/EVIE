# EVIE Commons · React GitHub Pages

## Architecture
The `web/` directory is a static, public React/Vite frontend built from EVIE's checked-in minimal `app/shelf/architecture_cards.json`. It does not need EVIE's FastAPI, Streamlit, model keys, local vault, scheduler, or databases. Historic card claims are separated visually from the one bounded CAD adapter available in the Python API.

Features: Overview; searchable Sovereign Shelf; original card input/output inspection; two archived ritual sequences; browser-only concept blueprint fixture that downloads `openblueprint.evie-proposal/1` for explicit user review in OpenBlueprint.

**Security**: no API credentials embedded, no privileged execution, no hosted backend connection, no automatic imports. The CAD demo is marked `source.mode=fixture`, NOT a real authenticated EVIE producer. The 11 card records come from canonical EVIE Shelf JSON at build time; do not hardcode/duplicate source catalogs.

## Run
From repository root:
```sh
cd web
npm ci
npm test
npm run dev
npm run build
```
The `sync:shelf` script synchronizes the canonical catalog before dev, test, and build.

## Publish
1. Merge the PR to `main`.
2. In repository Settings → Pages, select **GitHub Actions**.
3. Run **EVIE React Pages** if needed; pushes to web/ and the catalog also trigger it.
4. Expected URL: https://michaelwave369.github.io/EVIE/

## Limitations and follow-up
GitHub Pages is static: it cannot host EVIE's Python modules or vault API. Authentication, agent authority, and the live backend dashboard stay local. Use backend module `openblueprint_floor_plan` for actual local generated JSON; the public website's browser-only demo never pretends to execute it. Historical DXF/SVG outputs are NOT implemented by that module.


## Full Nested Sovereign Shelf (R4)

**Full Sovereign Shelf** in the React sidebar explores the privacy-minimized 159-card public archive across all 9 historical packs and 7 classes. Each card opens its original input/output contracts, nested ritual/mandate sequences and compatibility links. Add cards to a design-only deck, reorder, review dependency hints and export a JSON draft. **The public deck has no executor or API access.** The 11-card Architecture Pack and the original CAD fixture workshop remain independently available.

Reviewed source: `app/shelf/public_nested_catalog.json`. Generated UI snapshot synchronized by `web/scripts/sync-shelf.mjs`. Original full source archive remains in the owner's Library and is not published. See `docs/PUBLIC_NESTED_SHELF_R4.md`.


## Capability Mission Control (R6)

The public React **Mission Control** tab is a static source-derived snapshot of EVIE's real Python module registry and configured workflows. A deterministic Node exporter (`web/scripts/mission-audit.mjs`) reads those files during every frontend dev/test/build. It counts registered modules and referenced dependencies, but never tests live providers, calls the local EVIE API, imports Python, sends credentials, or executes a workflow. Historical job cards remain a separate inventory.

**Evidence discipline:** Only the bounded CAD producer has targeted test-source evidence indexed at this stage. Every other module is marked registered-only. The site claims **zero live runtime qualifications** and clearly labels risk-review hints as heuristics. See `docs/EVIE_MISSION_CONTROL_R6.md` and the local doctor at `python -m tools.evie_doctor --json --smoke-cad`.


## Qualification Lab (R7)

Mission Control → **Qualification Lab** explains the single allowlisted local CAD smoke scenario and lets you inspect a JSON receipt selected from your own computer. Validation is entirely in the browser, no uploads or persistence. The uploaded file is explicitly an *unsigned self-report* and cannot independently prove execution. The public live-qualified count stays zero. See `docs/EVIE_QUALIFICATION_LAB_R7.md` in the repository.


## R8: Verify a signed local qualification

Mission Control → Qualification Lab offers two-file, browser-only Ed25519 verification. Select the signed attestation and a trusted PUBLIC KEY PEM obtained through an independent channel. Files never leave the browser. A matching signature proves key control over the signed bytes, **not** that the reported test actually ran, nor that any operation is authorized. Global runtime-qualified count stays zero. See docs/EVIE_SIGNED_ATTESTATION_R8.md.


## R8B Family Gate

The public sidebar includes a **Family Gate** preview for six proposed ecosystem routes. The browser hashes a locally selected file (8 MB maximum), creates a time-limited `evie.family-handoff-proposal/1` review-only JSON, and downloads it without uploading the original. There is no remote transfer, credential exchange, action permission, or recipient adapter. Locally, `python -m tools.evie_family_gate` supports catalog, prepare, Ed25519 acknowledgement, and independent verification. See `docs/EVIE_FAMILY_GATE_R8B.md`.


## R9: Check real OpenBlue artifact bytes

The Family Gate now includes a two-file OpenBlue inspector. Select the R8B review envelope and its referenced blueprint JSON. The browser validates SHA-256 and byte length, expiry, destination, and supported wall/symbol geometry. This runs entirely in-browser with **no upload, no transport, no project changes, and no recipient acceptance**. After a PASS, independently open OpenBlue's existing EVIE CAD review UI to inspect and approve the plan. Details: `docs/EVIE_OPENBLUE_PREFLIGHT_R9.md`.


## R10 OpenBlue parser compatibility

After a R9 local file preflight, the Family Gate can optionally inspect an unsigned JSON report from the R10 command-line conformance runner. The runner uses an expressly selected local OpenBlue git revision and exercises its real parser. The browser only compares the report's fields with the already-inspected file digest/nonce; no upload, authentication or CAD import is implied. A separate pinned cross-repo GitHub Action tests parser compatibility in CI. See `docs/EVIE_OPENBLUE_PARSER_REPLAY_R10.md`.


## R11: FieldDeck human-reviewed blueprint bridge

Family Gate now includes a locally operated EVIE draft inspector + FieldDeck blueprint designer. Open an exported EVIE Sovereign Shelf design draft, independently select 1–6 of FieldDeck's reviewed action IDs, and export a default-deny FieldDeck v0.5 JSON. FieldDeck's actual parser is tested against it in pinned CI. No automatic EVIE-card mapping, upload, IssueOps submission, or runtime grant. See `docs/EVIE_FIELDDECK_HANDOFF_R11.md`.
