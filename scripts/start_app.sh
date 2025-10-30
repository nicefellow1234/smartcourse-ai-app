#!/usr/bin/env bash
#
# Helper to launch the SmartCourse Flask app with the expected environment.
#
# Usage:
#   ./scripts/start_app.sh             # runs on port 5000 by default
#   SMARTCOURSE_PORT=8000 ./scripts/start_app.sh
#   SMARTCOURSE_MAX_RESULTS=20 ./scripts/start_app.sh
#
# Assumes a virtual environment exists at .venv and all dependencies are installed.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ ! -d ".venv" ]]; then
  echo "error: virtual environment '.venv' not found. Run 'python3.10 -m venv .venv' first." >&2
  exit 1
fi

source .venv/bin/activate

export SMARTCOURSE_MODEL_DIR="${SMARTCOURSE_MODEL_DIR:-models}"
export SMARTCOURSE_MAX_RESULTS="${SMARTCOURSE_MAX_RESULTS:-10}"
export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+":$PYTHONPATH"}"

PORT="${SMARTCOURSE_PORT:-5000}"

echo "Starting SmartCourse on http://127.0.0.1:${PORT}"
echo "Using virtualenv: .venv"
echo "Model directory: ${SMARTCOURSE_MODEL_DIR}"
echo "Max results: ${SMARTCOURSE_MAX_RESULTS}"

exec python app.py --port "${PORT}"
