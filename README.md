# Open Valley

Open Valley is a work-in-progress civic-data project for Vermont's Mad River
Valley. Warren is the only public release today.

The public site presents a redacted, source-led baseline: public parcel map
features, `HSDECL` homestead-filing observations, coverage, and provider-level
provenance. It is designed to show what the records say and where they are
incomplete.

## What the public release does not say

Neither a homestead nor a non-homestead observation establishes occupancy,
residency, rental activity, commercial use, or second-home use. Open Valley does
not publish owner names, mailing addresses, review records, or raw source rows.

## Public release boundary

The public application reads only the versioned artifacts in `releases/`.
Protected source imports, personal data, and review records are handled outside
the public deployment. The public API provides release summary, map, homestead
trend, provider descriptors, and health information only.

## How it is built

Open Valley is a small data system as well as a web application. Public
municipal assessment/tax records, parcel GIS data, and supplemental public
property-transfer records are imported into a protected Postgres evidence
ledger. The import workflow validates provenance, joins, counts, and coverage;
it then produces a versioned JSON/GeoJSON release through a strict public-field
allowlist. The release is what powers the map and aggregate trends.

The stack is:

- **Web:** Next.js, React, TypeScript, Tailwind CSS, and MapLibre GL.
- **Public API:** Python, FastAPI, and Pydantic.
- **Protected data workflow:** PostgreSQL and Python import/release tooling.
- **Packaging:** separate Docker images for the web application and API.

The project uses LLM-assisted development as a fast, reviewable pairing
workflow: changes are developed in small units, checked locally, and verified
with tests and release validation. The data model, publication boundary, and
release criteria remain explicit code and human-reviewed decisions.

## Deployment

The public site runs as a two-service Docker Compose deployment. The Next.js
service serves the web app and proxies same-origin `/api/baseline/*` requests to
the FastAPI service; browsers never receive a database address or direct access
to a protected API. The API container contains only the release reader and
approved redacted artifacts. It has no protected-ledger credentials, and raw
source data and human review records are excluded from the public runtime.

See [the methodology](docs/methodology.md) for definitions and limits, and
[operations](docs/operations.md) for the release workflow and local preview.

## Local preview

The dashboard makes same-origin requests. Start the release-reader API and the
web app in separate terminals:

```bash
uv run uvicorn src.warren_baseline.app:app --host 127.0.0.1 --port 8998
cd web && npm install && npm run dev -- -p 3999
```

Open <http://localhost:3999/>. This preview is valid only with a generated,
redacted public release; do not point it at a raw-data directory or database.
