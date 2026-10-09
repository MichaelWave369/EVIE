# EVIE Local Revival: Rung 5

## Restore the engine, not just its website
EVIE's GitHub Pages React website is a static catalog. The real EVIE engine is Python/FastAPI with a Streamlit dashboard, modules, workflows and private data.

The currently registered source includes 117 modules and 10 configured workflows. Registration is **not** evidence that every module runs or that every provider is reachable. The 159 Sovereign Shelf cards are a separate historical catalog.

## Safer local defaults
- Windows and POSIX API and dashboard launch scripts now bind to **127.0.0.1**.
- Docker Compose maps ports to host 127.0.0.1 only, requiring an explicitly supplied EV_API_KEY.
- Protected FastAPI routes reject blank and documented sample keys (HTTP 503 for unsafe configuration). Wrong credentials return HTTP 401.
- This does not make the Python engine safe for exposure on the public internet. Do not port-forward or publish until a separate security audit.

## Quick start (Windows)
1. Clone the EVIE repository and install Python dependencies using a local virtual environment.
2. Copy .env.example to .env, replace EV_API_KEY with a unique random secret of at least 24 characters; select a model actually installed locally for Ollama.
3. From the repo root, run: python -m tools.evie_doctor --json --smoke-cad
4. Run .\start_api.ps1 then in a second terminal .\start_dashboard.ps1.
5. Open http://127.0.0.1:8501. Private API docs are at http://127.0.0.1:18791/docs.

For Linux/macOS, use bash start_api.sh and bash start_dashboard.sh instead.

## What EVIE Doctor verifies
- Source-registered modules and configured workflows (not proof of runtime execution).
- Broken module and nested-workflow references.
- Configured API key status, never its value.
- Optional --smoke-cad executes only the deterministic OpenBlueprint concept-JSON generator in a temporary directory and verifies file schema and SHA-256 digest, leaving no persistent artifacts.
- No external network calls, model jobs or live publishing occur in the doctor.

## Family revival roadmap
OpenBlueprint: producer/importer file handoff is implemented, still gated by human approval.
FieldDeck: future governed job-card and workflow runner.
PhiOS: future capability indexing behind action grants.
SuperPhiVessel: future routing/provider interoperability, with local secrets held locally.
Domistika/PixelForge: future artifact exchanges, not currently implemented in EVIE.

Tests: pytest -q tests/test_evie_local_revival.py
