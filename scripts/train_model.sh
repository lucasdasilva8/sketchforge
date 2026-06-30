#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/ml"

source "$ROOT/backend/.venv/bin/activate"
export PYTHONPATH="$ROOT/ml:$ROOT/backend:${PYTHONPATH:-}"

echo "Step 1/3 — Generate synthetic sketch dataset (2000 samples)..."
python dataset/generate_synthetic.py --count 2000

echo ""
echo "Step 2/3 — Export any real feedback from app usage..."
python dataset/export_feedback.py

echo ""
echo "Step 3/3 — Train model (15 epochs)..."
python train.py --epochs 15 --batch-size 32

echo ""
echo "Step 4/4 — Evaluate on synthetic holdout..."
python evaluate.py

echo ""
echo "Done! Checkpoint saved to ml/checkpoints/sketch_cad.pt"
echo "Restart the backend to load the new model."
