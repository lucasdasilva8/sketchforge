#!/usr/bin/env bash
set -euo pipefail

# Train the model with extra furniture/chair examples and class weighting.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/ml"

source "$ROOT/backend/.venv/bin/activate"
export PYTHONPATH="$ROOT/ml:$ROOT/backend:${PYTHONPATH:-}"

COUNT="${SYNTHETIC_COUNT:-5000}"
CHAIR_MULT="${CHAIR_MULTIPLIER:-3}"
EPOCHS="${EPOCHS:-20}"
CHAIR_WEIGHT="${CHAIR_WEIGHT:-2.5}"

echo "Step 1/3 — Export feedback from app usage..."
python dataset/export_feedback.py

echo ""
echo "Step 2/3 — Train (${EPOCHS} epochs, ${COUNT} synthetic, chair ${CHAIR_MULT}x, weight ${CHAIR_WEIGHT})..."
TRAIN_ARGS=(
  --epochs "$EPOCHS"
  --batch-size 32
  --synthetic-count "$COUNT"
  --chair-multiplier "$CHAIR_MULT"
  --chair-weight "$CHAIR_WEIGHT"
  --regenerate
)
if [[ -f checkpoints/sketch_cad.pt ]]; then
  echo "  Fine-tuning from existing checkpoint"
  TRAIN_ARGS+=(--fine-tune)
fi
python train.py "${TRAIN_ARGS[@]}"

echo ""
echo "Step 3/3 — Evaluate..."
python evaluate.py

echo ""
echo "Done! Restart the backend to load ml/checkpoints/sketch_cad.pt"
