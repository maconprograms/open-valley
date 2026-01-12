## Quick Start

```bash
# Start database
docker compose up -d

# API (terminal 1)
cd api && uv sync && uv run uvicorn src.main:app --reload --port 8000

# Frontend (terminal 2)
cd										 web && npm install && npm run dev
```

Open http://localhost:3000 for the chat interface.*0

## 