# Open Valley

An evidence-first civic-data baseline for Warren, Vermont.

The active dashboard distinguishes tax accounts, housing-unit evidence,
homestead filings, owner mailing geography, and property-transfer events. It
does not classify a property as a second home or prove full-time residency from
a single field.

## Start the Warren baseline

Run these in separate terminals:

```bash
# Repository root: standalone baseline API
uv run uvicorn src.warren_baseline.app:app --host 127.0.0.1 --port 8998

# Dashboard
cd web
npm install
npm run dev -- -p 3999
```

Open <http://localhost:3999/>. The web app proxies `/api/baseline/*` to the
standalone API, so no legacy database or AI service is needed for this workflow.

## Where to start

- [Warren data README](warren/README.md) — canonical sources, coverage, refresh
  commands, and denominator definitions.
- [Project guide](CLAUDE.md) — active architecture, guardrails, and verification.
- [Documentation map](docs/README.md) — what is current, planned, audited, or
  historical context.

## Status

The current product scope is Warren only. The data model is designed to support
future comparisons with other HUUSD towns without changing the meaning of its
core records. Older database, chat, STR, and Front Porch Forum experiments are
retained as research context; they are not the source of truth for the active
baseline.
