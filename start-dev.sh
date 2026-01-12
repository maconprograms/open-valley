#!/bin/bash

# Open Valley - Development Startup Script
# Runs PostgreSQL, FastAPI backend, and Next.js frontend

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    kill $API_PID 2>/dev/null || true
    kill $WEB_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Kill any existing dev server processes
echo -e "${YELLOW}Cleaning up existing processes...${NC}"
pkill -f "uvicorn src.main:app" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
# Remove Next.js lock file if it exists
rm -f "$PROJECT_DIR/web/.next/dev/lock" 2>/dev/null || true
sleep 1

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Open Valley - Starting Development Server${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check Docker
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Start database
echo -e "${BLUE}[1/3]${NC} Starting PostgreSQL..."
docker compose up -d
echo -e "${GREEN}  ✓ Database ready${NC}"

# Wait for database to be healthy
echo -n "  Waiting for database..."
for i in {1..30}; do
    if docker exec openvalley-db pg_isready -U openvalley -d openvalley > /dev/null 2>&1; then
        echo -e " ${GREEN}ready${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

# Start API
echo -e "${BLUE}[2/3]${NC} Starting API server..."
cd "$PROJECT_DIR"
uv run uvicorn src.main:app --reload --port 8999 2>&1 | sed 's/^/  [API] /' &
API_PID=$!
sleep 2
echo -e "${GREEN}  ✓ API starting on http://localhost:8999${NC}"

# Start frontend
echo -e "${BLUE}[3/3]${NC} Starting frontend..."
cd "$PROJECT_DIR/web"
npm run dev -- -p 3999 2>&1 | sed 's/^/  [WEB] /' &
WEB_PID=$!
sleep 3
echo -e "${GREEN}  ✓ Frontend starting on http://localhost:3999${NC}"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  All services running!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${BLUE}Frontend:${NC}  http://localhost:3999"
echo -e "  ${BLUE}API:${NC}       http://localhost:8999"
echo -e "  ${BLUE}API Docs:${NC}  http://localhost:8999/docs"
echo -e "  ${BLUE}Database:${NC}  postgresql://localhost:5432/openvalley"
echo ""
echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop all services"
echo ""

# Wait for both processes
wait $API_PID $WEB_PID
