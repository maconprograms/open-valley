# Running the Warren baseline locally

Purpose: Start and verify the standalone Warren baseline locally.
Audience: Local developers and researchers.
Status: guide
Owner: Open Valley maintainers
Last updated: 2026-08-04

The active dashboard has two services and does not require PostgreSQL, Docker,
or the legacy AI/chat API.

## Start

From the repository root, open two terminals.

```bash
# Terminal 1 — baseline API
uv run uvicorn src.warren_baseline.app:app --host 127.0.0.1 --port 8998
```

```bash
# Terminal 2 — Next.js dashboard
cd web
npm install
npm run dev -- -p 3999
```

Visit <http://localhost:3999/>. The dashboard calls `/api/baseline/*` on its own
origin; Next.js proxies those requests to `http://localhost:8998` by default.

## Check that it is healthy

```bash
curl http://127.0.0.1:8998/api/baseline/summary
curl http://127.0.0.1:3999/api/baseline/summary
```

Both requests should return JSON. If port 3999 is listening but does not return
a response, stop the existing Next.js process, remove `web/.next/dev/lock`, and
start the dashboard command again.

## Optional legacy services

The repository still contains an earlier PostgreSQL, FastAPI, and chat workflow.
It is not needed for the Warren baseline and is intentionally not started by
these commands. Consult the historical documentation only when working on that
separate surface.
