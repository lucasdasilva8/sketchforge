#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate
export PYTHONPATH="$(dirname "$PWD"):$(dirname "$PWD")/ml:${PYTHONPATH:-}"
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}" --reload
