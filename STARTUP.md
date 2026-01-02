# 🚀 Open Valley - Startup Guide

## Quick Start (One Command!)

### macOS / Linux:
```bash
./start-dev.sh
```

This single command will:
1. ✅ Start the PostgreSQL database (Docker)
2. ✅ Open a new Terminal tab for the Python FastAPI backend
3. ✅ Open another Terminal tab for the Next.js frontend
4. ✅ Show you where to access the app

Then open your browser to: **http://localhost:3000**

---

## What the Script Does

The `start-dev.sh` script automates the full startup sequence:

```
1. Check if Docker is running
2. Start PostgreSQL database (docker compose up -d)
3. Open Terminal tab #1: API backend (uvicorn on port 8000)
4. Open Terminal tab #2: Frontend (Next.js on port 3000)
```

You'll end up with 3 services running:
- **🗄️ Database**: PostgreSQL on `localhost:5432`
- **🔗 API**: FastAPI on `localhost:8000`
- **🌐 Frontend**: Next.js on `localhost:3000`

---

## Manual Startup (If Script Doesn't Work)

If the script doesn't work for your setup, run these in **3 separate terminals**:

### Terminal 1: Database
```bash
docker compose up -d
```

### Terminal 2: Python API Backend
```bash
cd api
uv sync
uv run uvicorn src.main:app --reload --port 8000
```

### Terminal 3: Next.js Frontend
```bash
cd web
npm install
npm run dev
```

Then visit: **http://localhost:3000**

---

## Stopping Services

### With Docker (stops database only):
```bash
docker compose down
```

### Or use the helper script:
```bash
./stop-dev.sh
```

### Stop API & Frontend:
Press `Ctrl+C` in those terminal tabs.

---

## Accessing Your App

| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend** | http://localhost:3000 | Chat interface with visualizations |
| **API** | http://localhost:8000 | FastAPI server |
| **API Docs** | http://localhost:8000/docs | Interactive API documentation |
| **Database** | localhost:5432 | PostgreSQL (openvalley/openvalley) |

---

## Database Connection

Connect via psql:
```bash
docker compose exec db psql -U openvalley -d openvalley
```

Connection string:
```
postgresql://openvalley:openvalley@localhost:5432/openvalley
```

---

## Environment Setup

Create `api/.env` with your credentials:
```
DATABASE_URL=postgresql://openvalley:openvalley@localhost:5432/openvalley
PYDANTIC_AI_GATEWAY_API_KEY=your-gateway-key
OPENAI_API_KEY=your-openai-key
LOGFIRE_TOKEN=optional
```

---

## Troubleshooting

### Docker not running
- Make sure Docker Desktop is open
- The script will tell you if Docker isn't available

### Ports already in use
- Database port 5432: Change in `docker-compose.yml`
- API port 8000: Change `--port 8000` in the start script
- Frontend port 3000: Next.js will prompt to use 3001 if 3000 is taken

### Database connection errors
- Wait a few seconds after starting Docker for the database to initialize
- Check logs: `docker compose logs -f db`

### Dependencies not installing
- API: Make sure you have `uv` installed (`pip install uv`)
- Frontend: Make sure you have Node.js 18+ installed

---

## File Structure

```
open-valley/
├── start-dev.sh          ← Run this to start everything
├── stop-dev.sh           ← Run this to stop everything
├── docker-compose.yml    ← Database configuration
├── api/                  ← Python FastAPI backend
│   └── src/
│       ├── main.py       ← FastAPI app
│       ├── agent.py      ← Pydantic AI agent
│       └── models.py     ← Database models
└── web/                  ← Next.js frontend
    └── src/
        ├── app/
        └── components/
```

---

## Common Commands

```bash
# View database logs
docker compose logs -f db

# Connect to database
docker compose exec db psql -U openvalley -d openvalley

# Stop everything
docker compose down

# Remove database volume (reset data)
docker compose down -v

# Restart from scratch
docker compose down -v && docker compose up -d
```

---

## Architecture Overview

```
Frontend (Next.js, port 3000)
    ↓ (HTTP requests)
Backend API (FastAPI, port 8000)
    ↓ (SQL queries)
Database (PostgreSQL, port 5432)
```

The frontend talks to the API, which talks to the database. The AI agent runs in the API and has tools to query property data and community posts.

---

## Need Help?

- Check `CLAUDE.md` for the full project documentation
- Check individual `README.md` files in `api/` and `web/` directories
- View API docs at http://localhost:8000/docs once the API is running

Happy coding! 🎉