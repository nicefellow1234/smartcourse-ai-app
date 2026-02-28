#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOOTSTRAP="$SCRIPT_DIR/scripts/start_project.py"

if [[ ! -f "$BOOTSTRAP" ]]; then
  echo "Bootstrap script not found: $BOOTSTRAP" >&2
  exit 1
fi

PYTHON_CMD=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_CMD="python"
fi

if [[ -z "$PYTHON_CMD" ]]; then
  echo "Python 3.10+ is required but was not found."
  echo "Install Python and run again:"
  echo "  ./start_project.sh"
  echo ""
  if command -v apt-get >/dev/null 2>&1; then
    echo "Ubuntu/Debian example:"
    echo "  sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip"
  elif command -v dnf >/dev/null 2>&1; then
    echo "Fedora example:"
    echo "  sudo dnf install -y python3 python3-pip"
  elif command -v pacman >/dev/null 2>&1; then
    echo "Arch example:"
    echo "  sudo pacman -Sy --noconfirm python python-pip"
  fi
  exit 1
fi

echo "Using Python launcher: $PYTHON_CMD"
cd "$SCRIPT_DIR"
exec "$PYTHON_CMD" "$BOOTSTRAP" "$@"
