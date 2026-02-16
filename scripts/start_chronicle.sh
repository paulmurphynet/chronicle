#!/usr/bin/env bash
# Start the Chronicle API and frontend; open the welcome screen.
# Run from repo root. Requires: venv with [api] installed, frontend deps installed.

set -e
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

# Activate venv if present so uvicorn is on PATH
if [ -d "$ROOT/.venv" ]; then
  source "$ROOT/.venv/bin/activate"
fi

# Kill API when this script exits (e.g. Ctrl+C)
cleanup() {
  if [ -n "$UVICORN_PID" ]; then
    kill "$UVICORN_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

echo "Starting Chronicle API on http://localhost:8000 ..."
uvicorn chronicle.api.app:app --reload &
UVICORN_PID=$!

# Give API a moment to bind
sleep 2

echo "Starting frontend on http://localhost:5173 ..."
echo ""
echo "  Welcome screen: http://localhost:5173"
echo "  (Stop with Ctrl+C)"
echo ""

cd "$ROOT/frontend"
exec npm run dev
