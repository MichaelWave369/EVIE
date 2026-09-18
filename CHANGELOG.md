# CHANGELOG — EmberVault Income Engine (EVIE)

## v3.1.0 — 2026-02-14

### Bug Fixes (Critical)
- **factory.py**: Fixed `run_id` referenced before assignment in `run_next()` — this crashed every Factory queue build
- **builder.py**: Fixed escaped newlines (`\\n`) in CHANGELOG and README.txt that wrote literal backslash-n instead of actual line breaks
- **dashboard/app.py**: Fixed variable shadowing — `up` (file uploader) was defined twice causing wrong file sent to wrong endpoint; renamed to `ingest_upload` / `metrics_upload`
- **dashboard/app.py**: Fixed variable shadowing — `run_id` defined as both text input and number input; renamed to `run_detail_id` / `metrics_run_id`

### Performance
- **SQLite connection pooling**: Thread-local cached connections eliminate 100+ open/close cycles per flywheel build
- **FAISS index caching**: Loaded index cached in memory with mtime invalidation — avoids 50-200ms disk read per search
- **Configurable LLM timeout**: `EV_OLLAMA_TIMEOUT` (default 600s, was hardcoded 120s) — prevents timeout on long ebook generation
- **Module retry with backoff**: Modules that fail in flywheel builds retry up to 2x with exponential backoff (1.5s, 3s) instead of failing the entire build

### New Features
- **`GET /health` endpoint**: Returns DB status, Ollama connectivity, version — no auth required, essential for Docker monitoring
- **Dashboard overhaul**: EmberVault-branded dark theme with ember/gold styling, API connectivity indicator, spinner feedback on all operations, expander-based results display instead of raw JSON dumps, new Dashboard tab with live metric cards
- **Logging**: Flywheel builder now uses Python logging (`evie.flywheel`) for module execution, retries, and errors

### Internal
- Version bumped to 3.1.0 across FastAPI app, feature manifest, and dashboard
- All Streamlit widgets now have explicit `key=` parameters to prevent state collisions
