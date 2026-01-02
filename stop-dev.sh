#!/bin/bash

# Open Valley - Development Stop Script
# Stops PostgreSQL database and cleans up

set -e

echo "🛑 Stopping Open Valley services..."
echo ""

# Stop Docker database
echo "Stopping PostgreSQL database..."
docker compose down
echo "✅ Database stopped"
echo ""

echo "════════════════════════════════════════════"
echo "✅ All services stopped!"
echo "════════════════════════════════════════════"
echo ""
echo "Note: API and Frontend servers should be stopped manually"
echo "      (Ctrl+C in their respective terminal tabs)"
echo ""
