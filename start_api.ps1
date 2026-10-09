# EVIE local-first API launcher. Keep this loopback-only unless separately audited.
Write-Host "Starting EVIE API at http://127.0.0.1:18791" -ForegroundColor Cyan
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 18791
