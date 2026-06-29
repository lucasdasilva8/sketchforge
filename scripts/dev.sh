#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

if ! command -v node >/dev/null 2>&1; then
  echo "Node.js is required. Install with: brew install node"
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required. Install with: brew install node"
  exit 1
fi

# Backend venv
if [[ ! -d "$ROOT/backend/.venv" ]]; then
  echo "Creating Python virtualenv..."
  python3 -m venv "$ROOT/backend/.venv"
  source "$ROOT/backend/.venv/bin/activate"
  pip install -r "$ROOT/backend/requirements.txt"
else
  source "$ROOT/backend/.venv/bin/activate"
fi

# Frontend deps
if [[ ! -d "$ROOT/frontend/node_modules" ]]; then
  echo "Installing frontend dependencies..."
  (cd "$ROOT/frontend" && npm install)
fi

export PYTHONPATH="$ROOT/backend:$ROOT/ml:${PYTHONPATH:-}"

cleanup() {
  echo ""
  echo "Stopping servers..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting backend on http://127.0.0.1:8000"
(cd "$ROOT/backend" && uvicorn main:app --host 127.0.0.1 --port 8000 --reload) &
BACKEND_PID=$!

sleep 1

if ! curl -sf http://127.0.0.1:8000/health >/dev/null; then
  echo "Backend failed to start. Check Python dependencies:"
  echo "  cd backend && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

echo "Starting frontend on http://127.0.0.1:5173"
(cd "$ROOT/frontend" && npm run dev -- --host 127.0.0.1) &
FRONTEND_PID=$!

echo ""
echo "SketchForge is running:"
echo "  App:     http://127.0.0.1:5173"
echo "  API:     http://127.0.0.1:8000"
echo ""
echo "Press Ctrl+C to stop both servers."

wait
