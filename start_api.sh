#!/usr/bin/env bash
set -e
if [ ! -f ".env" ]; then
  echo "No .env configured. Copy .env.example and set a unique EV_API_KEY."
  exit 1
fi
echo "Starting EVIE local API: http://127.0.0.1:18791"
python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 18791
