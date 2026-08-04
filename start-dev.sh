#!/bin/bash

# Open Valley - Warren baseline development startup script

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

cleanup() {
    kill "$API_PID" 2>/dev/null || true
    kill "$WEB_PID" 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

pkill -f "uvicorn src.warren_baseline.app:app" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true

uv run uvicorn src.warren_baseline.app:app --reload --port 8998 &
API_PID=$!

(
    cd "$PROJECT_DIR/web"
    npm run dev -- -p 3999
) &
WEB_PID=$!

echo "Frontend: http://localhost:3999"
echo "Warren baseline API: http://localhost:8998"
echo "API docs: http://localhost:8998/docs"

wait "$API_PID" "$WEB_PID"
