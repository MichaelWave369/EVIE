from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse, Response
from app.db.migrate import main as migrate_main
from app.api.routes_ingest import router as ingest_router
from app.api.routes_search import router as search_router
from app.api.routes_rag import router as rag_router
from app.api.routes_modules import router as modules_router
from app.api.routes_products import router as products_router
from app.api.routes_campaigns import router as campaigns_router
from app.api.routes_evidence import router as evidence_router
from app.api.routes_workflows import router as workflows_router
from app.api.routes_flywheel import router as flywheel_router
from app.api.routes_admin import router as admin_router
from app.api.routes_metrics import router as metrics_router
from app.api.routes_factory import router as factory_router
from app.api.routes_scheduler import router as scheduler_router
from app.api.routes_runs import router as runs_router
from app.api.routes_swarm import router as swarm_router
from app.scheduler.runner import start_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # DB migrations + optional scheduler (local-only)
    migrate_main()
    sched = start_scheduler()
    app.state.scheduler = sched
    try:
        yield
    finally:
        try:
            if sched:
                sched.shutdown()
        except Exception:
            pass

app = FastAPI(
    title="EmberVault Income Engine (EVIE) — Local-Only",
    version="3.2.0",
    lifespan=lifespan,
)

# ---- Friendly landing page (no auth required) ----
@app.get("/", include_in_schema=False)
async def root():
    return HTMLResponse(
        """<!doctype html>
<html>
  <head><meta charset="utf-8"><title>EVIE v3.2</title></head>
  <body style="font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; padding: 24px;">
    <h1>EVIE v3.2 is running ✅</h1>
    <p>This server is an API (so <code>/</code> used to return 404). Use these links:</p>
    <ul>
      <li><a href="/docs">/docs</a> — interactive API explorer (Swagger)</li>
      <li><a href="/redoc">/redoc</a> — alternative API docs</li>
      <li><a href="/health">/health</a> — health check JSON</li>
      <li><a href="/openapi.json">/openapi.json</a> — OpenAPI schema</li>
    </ul>
    <p><b>Auth:</b> most endpoints require an <code>X-API-Key</code> header (your <code>EV_API_KEY</code>).</p>
  </body>
</html>"""
    )

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    # Prevent noisy 404s in the terminal logs
    return Response(status_code=204)

# ---- Health check (no auth required) ----
@app.get("/health", tags=["system"])
async def health():
    """Health check for Docker monitoring and dashboard connectivity."""
    import datetime
    from app.settings import settings
    checks = {"status": "ok", "version": "3.2.0", "ts": datetime.datetime.utcnow().isoformat()}
    # DB check
    try:
        from app.db.schema import connect
        con = connect()
        con.execute("SELECT 1")
        checks["db"] = "ok"
    except Exception as e:
        checks["db"] = f"error: {e}"
        checks["status"] = "degraded"
    # Ollama check (best-effort, non-blocking)
    if settings.llm_backend == "ollama":
        try:
            import requests as _req
            _r = _req.get(settings.ollama_base_url.rstrip("/") + "/api/tags", timeout=3)
            checks["ollama"] = "ok" if _r.status_code == 200 else f"status {_r.status_code}"
        except Exception:
            checks["ollama"] = "unreachable"
    else:
        checks["ollama"] = "disabled"
    return JSONResponse(checks)

app.include_router(ingest_router)
app.include_router(search_router)
app.include_router(rag_router)
app.include_router(modules_router)
app.include_router(products_router)
app.include_router(campaigns_router)
app.include_router(evidence_router)
app.include_router(workflows_router)
app.include_router(flywheel_router)
app.include_router(admin_router)
app.include_router(metrics_router)
app.include_router(factory_router)
app.include_router(scheduler_router)
app.include_router(runs_router)
app.include_router(swarm_router)
