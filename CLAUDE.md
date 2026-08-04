# Open Valley — Warren evidence-first baseline

Purpose: Define the active product boundary, data guardrails, and contributor workflow.
Audience: Contributors and coding agents working on the Warren baseline.
Status: guide
Owner: Open Valley maintainers
Last updated: 2026-08-04

Open Valley is a local civic-data project that begins with Warren, Vermont. The
active product is a map-first baseline for property accounts, housing-unit
evidence, homestead filings, and transfer records.
It is designed to establish checkable facts before drawing conclusions about
second homes, full-time residency, or housing pressure.

## Product rules

- A **tax account** is not a housing unit. Always show their denominators
  separately.
- A filed homestead declaration (`HSDECL`) is an observed tax field, **not**
  proof that someone lives there full time.
- Owner mailing observations are retained in the private research ledger, but
  never classify or color the map.
- Source-exact owner names remain evidence; any normalized party is a separate,
  confidence-scored interpretation.
- Preserve unknowns, unmatched records, source dates, and coverage. Do not fill
  gaps with inferred facts.

## Active architecture

The standalone baseline intentionally does not import the legacy database or AI
application.

```text
warren source extracts and historical snapshots
  -> warren/scripts/build_baseline.py
  -> immutable source runs in warren/outputs/baseline/runs/
  -> manifest.json selects one validated current run
  -> src/warren_baseline FastAPI API (port 8998)
  -> Next.js dashboard and MapLibre map (port 3999 in this workspace)
```

`src/warren_baseline/` is the authoritative read model for the active
dashboard. Its JSONL ledger contains separate records for property accounts,
parcel geometry references, housing-unit claims, assessment snapshots, ownership
observations, transfer events, source records, and normalized-party matches.

The map projection is deliberately privacy-preserving: it does not expose owner
names or mailing street addresses. `/api/baseline/accounts/{account_id}` is a
research-detail endpoint and must be redacted or access-controlled before any
public deployment.

## Important paths

| Need | Location |
|---|---|
| Current data inventory, refresh steps, and denominators | `warren/README.md` |
| Baseline API and repository | `src/warren_baseline/` |
| Baseline UI | `web/src/components/baseline/` |
| Data materialization tests | `tests/warren_baseline/` |
| Implementation plan | `docs/plans/2026-08-03-001-feat-warren-baseline-dashboard-plan.md` |
| Current documentation map | `docs/README.md` |
| Audit history and remaining safeguards | `docs/audit/2026-08-04-audit-report.md` |

The former database, chat, STR, FPF, and transition-analysis runtime has been
removed. Historical source extracts and research documentation are retained as
context, but may not replace the baseline's definitions or figures without a
reviewed reconciliation.

## Local development

Run these in separate terminals from the repository root:

```bash
# Standalone Warren baseline API
uv run uvicorn src.warren_baseline.app:app --host 127.0.0.1 --port 8998

# Dashboard
cd web
npm install
npm run dev -- -p 3999
```

Open `http://localhost:3999/`. The Next.js rewrite proxies `/api/baseline/*` to
port 8998 by default, so the dashboard uses same-origin requests. For a deployed
environment, set `INTERNAL_BASELINE_API_URL`; only set
`NEXT_PUBLIC_BASELINE_API_URL` when a direct, CORS-configured API is intended.

## Data refresh

See `warren/README.md` for the full source catalog and caveats. The normal
baseline refresh is:

```bash
uv run python warren/scripts/join_nemrc_vcgi.py
uv run python warren/scripts/fetch_pttr_baseline.py
uv run python -m warren.scripts.build_baseline --pttr warren/outputs/warren_pttr.json
```

Promote only a validated run after reviewing its source coverage and derived map
projection. Never edit a prior run in place. Historical homestead observations
are rebuilt separately with:

```bash
uv run python warren/scripts/extract_historical_homesteads.py
```

## Verification

```bash
# Python baseline suite (the explicit module form is intentional)
uv run python -m unittest \
  tests.warren_baseline.test_build_baseline \
  tests.warren_baseline.test_repository \
  tests.warren_baseline.test_schema \
  tests.warren_baseline.test_api

cd web
npm test
npx eslint src/components/baseline src/app/layout.tsx
npm run build
```

The full frontend lint command currently reports unrelated legacy errors. Do not
silence those errors in baseline work; address them in a separately scoped
cleanup.
