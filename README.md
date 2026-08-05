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

## Repository status

This repository is being prepared for public release. A history-remediation
step is still required before launch because earlier commits contained data that
does not belong in a public project. Removing history reduces exposure but
cannot retract existing clones or forks.
