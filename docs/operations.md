# Operations

## Public release workflow

1. An authorized operator imports a source run into the protected ledger and
   validates counts and aggregate checksums.
2. The exporter builds a versioned, strictly allowlisted public release.
3. Public-release validation checks schemas, provenance, coverage, freshness,
   and restricted fields or values. Failures leave the previous release in
   place and report only safe artifact and field paths.
4. Commit only the redacted release artifacts. The public API and web service
   read those artifacts; neither has database credentials.
5. Verify the dashboard, public API, keyboard parcel list, and unavailable
   states before routing the public hostname.

Private imports, protected database credentials, backups, and human review are
operator-only work. Keep them out of terminals captured for public logs, CI,
repository files, container images, and support tickets.

## Local public-artifact preview

Run the release-reader API and Next.js app separately:

```bash
uv run uvicorn src.warren_baseline.app:app --host 127.0.0.1 --port 8998
cd web && npm install && npm run dev -- -p 3999
```

Use same-origin `/api/baseline/*` requests only. The production web service
proxies internally to the release-reader API; browsers never receive a direct
database or private API address.

## Checks

```bash
uv run python -m unittest
cd web && npm test && npm run lint && npm run build
```

The full public-release guardrail and deployment validation are required before
launch. The sensitive-data history rewrite and DNS cutover are operator-owned,
destructive release steps; do not perform them from a feature branch.
