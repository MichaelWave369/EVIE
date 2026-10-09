# Local-only Streamlit dashboard for EVIE.
Write-Host "Starting EVIE Dashboard at http://127.0.0.1:8501" -ForegroundColor Cyan
python -m streamlit run dashboard/app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
