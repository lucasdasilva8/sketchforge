#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Setting up SketchForge backend..."
cd "$ROOT/backend"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

echo "Setting up SketchForge frontend..."
cd "$ROOT/frontend"
npm install

echo "Training bootstrap ML checkpoint..."
cd "$ROOT"
source backend/.venv/bin/activate
python ml/train.py --epochs 2

echo "Done. Run backend: cd backend && source .venv/bin/activate && uvicorn main:app --reload"
echo "Run frontend: cd frontend && npm run dev"
