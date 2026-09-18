# ============================================================
# EVIE v4.0 — Start Dashboard (Windows PowerShell)
# ============================================================
Write-Host "Starting EVIE Dashboard on http://localhost:8501" -ForegroundColor Cyan
python -m streamlit run dashboard/app.py --server.port 8501 --server.headless true
