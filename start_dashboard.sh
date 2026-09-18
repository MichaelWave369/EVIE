#!/usr/bin/env bash
# ============================================================
# EVIE v4.0 — Start the Dashboard UI
# Run this in a SECOND terminal window (after start_api.sh).
# ============================================================
set -e

echo "🔥 Starting EVIE Dashboard on http://localhost:8501"
echo "   Press CTRL+C to stop"
echo ""

python3 -m streamlit run dashboard/app.py --server.port 8501 --server.headless true
