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
