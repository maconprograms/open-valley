#!/bin/bash

# Open Valley - Development Startup Script
# Launches PostgreSQL (Docker), FastAPI backend, and Next.js frontend

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🚀 Starting Open Valley...${NC}"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${YELLOW}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Start the database
echo -e "${BLUE}1️⃣  Starting PostgreSQL database...${NC}"
docker compose up -d
sleep 3
echo -e "${GREEN}✓ Database running on port 5432${NC}"
echo ""

# Function to open terminal based on OS
open_new_terminal() {
    local title=$1
    local command=$2

    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        osascript <<EOF
tell application "Terminal"
    activate
    tell application "System Events" to keystroke "t" using command down
    delay 0.5
    do script "$command" in front window
end tell
EOF
    elif command -v gnome-terminal &> /dev/null; then
        # Linux with GNOME Terminal
        gnome-terminal --tab --title="$title" -- bash -c "$command; exec bash"
    elif command -v konsole &> /dev/null; then
        # Linux with KDE Konsole
        konsole --new-tab -e bash -c "$command; exec bash" &
    elif command -v xterm &> /dev/null; then
        # Fallback to xterm
        xterm -title "$title" -e bash -c "$command; exec bash" &
    else
        echo -e "${YELLOW}Warning: Could not auto-open terminal. Please run manually:${NC}"
        echo "$command"
        return 1
    fi
}

# Start the API backend
echo -e "${BLUE}2️⃣  Opening terminal for FastAPI backend...${NC}"
API_CMD="cd '$PROJECT_DIR/api' && uv sync && uv run uvicorn src.main:app --reload --port 8999"
open_new_terminal "API" "$API_CMD"
sleep 1
echo -e "${GREEN}✓ API terminal opened${NC}"
echo ""

# Start the frontend
echo -e "${BLUE}3️⃣  Opening terminal for Next.js frontend...${NC}"
WEB_CMD="cd '$PROJECT_DIR/web' && npm install && npm run dev -- -p 3999"
open_new_terminal "Frontend" "$WEB_CMD"
sleep 1
echo -e "${GREEN}✓ Frontend terminal opened${NC}"
echo ""

echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ All services started!${NC}"
echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo ""
echo "📍 Open your browser to: ${BLUE}http://localhost:3999${NC}"
echo ""
echo "Services running:"
echo "  🗄️  Database:  postgresql://localhost:5432/openvalley"
echo "  🔗 API:       http://localhost:8999"
echo "  🌐 Frontend:  http://localhost:3999"
echo ""
echo "Useful links:"
echo "  📚 API Docs:  http://localhost:8999/docs"
echo ""
echo "To stop all services:"
echo "  ${YELLOW}docker compose down${NC}"
echo ""
