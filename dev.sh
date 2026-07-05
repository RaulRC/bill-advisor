#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "==> Starting FastAPI on :8000 ..."
.venv/bin/python -m uvicorn api.main:app --reload --port 8000 &
API_PID=$!

echo "==> Starting Vite on :3000 (proxies /api -> :8000) ..."
cd "$ROOT/frontend"
npm run dev &
VITE_PID=$!

trap "kill $API_PID $VITE_PID 2>/dev/null; exit" INT TERM

echo ""
echo "  📊  App  →  http://localhost:3000"
echo "  🔌  API  →  http://localhost:8000/api/health"
echo "  ⏎  Ctrl+C to stop"
echo ""

wait
