# ============================================================
# EVIE v4.0 — Start API Server (Windows PowerShell)
# ============================================================
Write-Host "Starting EVIE API Server on http://localhost:18791" -ForegroundColor Cyan
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 18791
