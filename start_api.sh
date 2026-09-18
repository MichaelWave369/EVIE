#!/usr/bin/env bash
# ============================================================
# EVIE v4.0 — Start the API Server
# Run this in one terminal window.
# ============================================================
set -e

if [ ! -f ".env" ]; then
    echo "❌ No .env file found! Run: bash setup.sh first"
    exit 1
fi

echo "🔥 Starting EVIE API Server on http://localhost:18791"
echo "   API docs: http://localhost:18791/docs"
echo "   Press CTRL+C to stop"
echo ""

python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 18791
