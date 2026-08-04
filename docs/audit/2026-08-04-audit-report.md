# Codebase Audit Report — Warren Baseline Dashboard

**Date:** 2026-08-04  
**Audited by:** Focused deep audit (Inspector, Stress Tester, Architect, Privacy Reviewer, Accessibility Reviewer)  
**Stack:** Next.js 16 / React 19 / TypeScript / MapLibre; FastAPI / Python; immutable JSONL and GeoJSON source ledger  
**Previous Audit:** First audit  
**Framework Docs Consulted:** Next.js, PydanticAI, Astral uv, Ruff `llms.txt`; FastAPI and Pydantic endpoints were unavailable to the audit client.

## Follow-up status — 2026-08-04

The map crash and the baseline-page performance issues identified in this audit
have been fixed. MapLibre properties are normalized and regression-tested before
they reach the click panel or hover tooltip; filters survive asynchronous layer
loading; legacy global map prefetches are gone; and the map endpoint streams its
immutable GeoJSON artifact. The dashboard now uses a same-origin baseline proxy,
and the frontend has an `npm test` command.

Remaining work is intentional follow-up: define a public-data boundary for the
raw account-detail endpoint, provide a non-pointer equivalent for parcel
inspection, finish repository-wide lint cleanup, and evaluate whether cached
per-run indexes are needed after measuring larger cross-town data.

## Executive Summary

The new Warren baseline is a sound, deliberately separate evidence-ledger surface: it keeps tax accounts and housing-unit claims distinct, preserves source runs, and redacts owner names from the map. Its immediate weakness is at the map/API boundary: runtime GeoJSON properties are trusted as TypeScript values, which directly caused the reported parcel-click crash. The active dashboard also pays for legacy requests and repeatedly parses a 6 MB map artifact, both of which are straightforward to remove.

**Original findings:** 1 Critical, 6 Significant, 3 Cleanup  
**Status:** 6 resolved, 1 partially resolved, 3 remaining

## Codebase Metrics

| Metric | Value |
|---|---:|
| Active baseline source files reviewed | 10 |
| Active baseline lines reviewed | 978 |
| Map artifact | 6.0 MB |
| Python baseline tests | 15 passing |
| Frontend unit tests | 3 passing |
| Frontend production build | Passing |
| Full frontend lint | 12 errors / 8 warnings, all outside `components/baseline` |
| TODO/FIXME/HACK count (whole repo) | 21 |
| Dependency health | Fair — lockfiles are present; the focused frontend test command is available |

## Punchlist

1. **[RESOLVED — CRITICAL]** Normalize MapLibre feature properties before rendering them — `web/src/components/baseline/mapProperties.ts`, `mapProperties.test.ts` — MapLibre array properties are parsed at the boundary, including serialized and malformed values.
2. **[RESOLVED — SIGNIFICANT]** Preserve a selected filter while map layers load — `web/src/components/baseline/BaselineMap.tsx` — the current filter is re-applied after layers load.
3. **[RESOLVED — SIGNIFICANT]** Stop prefetching legacy GeoJSON on every page — `web/src/app/layout.tsx` — baseline visits no longer make port-8999 map requests.
4. **[RESOLVED — SIGNIFICANT]** Serve the immutable GeoJSON artifact without parse-and-reencode work — `src/warren_baseline/api.py`, `repository.py` — `/map` now returns a `FileResponse` for the promoted artifact.
5. **[PARTIAL — SIGNIFICANT]** Avoid repeated JSONL work — `src/warren_baseline/repository.py` — record reads are cached by file mtime; per-request account indexes are still rebuilt and should be measured before further optimization.
6. **[OPEN — SIGNIFICANT]** Define a public-data boundary for account details — `src/warren_baseline/api.py`, `repository.py` — the unauthenticated detailed endpoint still returns raw ownership observations.
7. **[RESOLVED — SIGNIFICANT]** Make the standalone API deployable from the dashboard origin — `web/next.config.ts`, `BaselineDashboard.tsx` — baseline routes now use the same-origin proxy by default.
8. **[RESOLVED — CLEANUP]** Add a frontend unit-test command and map-property regression coverage — `web/package.json`, `mapProperties.test.ts`.
9. **[OPEN — CLEANUP]** Make parcel inspection available without pointer-only interaction — `web/src/components/baseline/BaselineMap.tsx` — hover and click improve investigation, but a keyboard-equivalent account browser remains needed.
10. **[OPEN — CLEANUP]** Establish canonical repository-wide quality commands — `pyproject.toml`, `tests/warren_baseline/` — the explicit Python command is documented, but Ruff is not installed and legacy ESLint failures remain.

## Deep Dive by Category

### Security & Data Minimization

The map projection intentionally excludes `owner_text` and mailing street address, which is the right default for a public community dashboard. In contrast, the account-detail endpoint exposes raw ownership observations without authentication. This is not a claim that the source data is secret; it is a deployment boundary that must be explicit before this local research tool becomes public. Gate the detailed ledger or publish a second, redacted detail projection. **OWASP:** A01 — Broken Access Control (if deployed publicly without the intended access boundary).

### Code Quality & Contract Safety

The click failure comes from a TypeScript assertion crossing a third-party runtime boundary. `event.features[0].properties` is untrusted data, not a `MapFeature` just because it is asserted as one. A small parser at that boundary protects the rest of the component from strings, missing fields, and malformed values; a pure unit test protects the behavior against future MapLibre changes.

### Performance & Resilience

The baseline is built around immutable promoted runs, which makes caching particularly safe: a request can reuse records for the current run and invalidate only when the manifest pointer changes. The current `/map` path reads and deserializes the 6 MB GeoJSON file, then FastAPI serializes it again. Serving the file directly retains the artifact exactly and removes that avoidable CPU and allocation cost. The global legacy GeoJSON prefetch has a similar effect in the browser: it consumes bandwidth and produces noisy failures for a baseline-only session without helping the active page.

### Organization & Dependencies

The standalone `src/warren_baseline` package is a healthy boundary from the legacy application. Do not re-couple it to legacy `src/main.py` merely to share infrastructure. The baseline now has a focused frontend test runner and regression coverage. The repo-wide ESLint gate still fails in older, out-of-scope files; schedule that cleanup separately rather than masking failures.

## Sprint Tasks

### Sprint 1: Restore map reliability and baseline-page performance

- [x] Normalize map properties, retain filters during load, clear stale selection, and add a frontend regression test. Addresses: #1, #2, #8.
- [x] Remove global legacy map prefetches and describe the baseline accurately in metadata. Addresses: #3.
- [x] Stream the immutable map artifact and cache current-run records. Addresses: #4; partially addresses #5.

### Sprint 2: Make the public API contract intentional

- [ ] Choose and document public versus research-only account fields; implement a redacted public DTO or access control before deployment. Addresses: #6.
- [x] Add same-origin proxying for baseline routes. Addresses: #7.

### Sprint 3: Repair repository-wide developer ergonomics

- [ ] Add Ruff as a development dependency and a documented test invocation; fix or isolate legacy ESLint failures in a separately scoped change. Addresses: #10.

## What's Working Well

- **Evidence-first data model** — tax accounts, unit claims, and observations are kept as separate primitives rather than collapsed into an unsupported second-home label.
- **Immutable source runs** — promotion builds the derived map before atomically switching the manifest, providing a reproducible read boundary.
- **Privacy-aware map projection** — owner names and street mailing addresses are intentionally absent from the public map.
- **Meaningful test coverage** — the backend materialization and API paths have 15 passing tests, and the production web build passes.

## Specialist Reports

<details><summary>Inspector, Stress Tester, Architect, Accessibility Reviewer</summary>

- Confirmed the active MapLibre property crash and the pre-load filter race.
- Confirmed global legacy prefetches run on the new baseline homepage.
- Confirmed pointer-only parcel inspection has no equivalent keyboard flow.
- Confirmed `map.geojson` is 6.0 MB and the endpoint currently parses/re-serializes it per request.
</details>

<details><summary>Privacy Reviewer</summary>

- Confirmed map PII redaction and the contrast with raw ownership details returned by `/accounts/{account_id}`.
- Confirmed the production API-origin/CORS contract is not yet represented in the Next rewrite configuration.
</details>

<details><summary>Test & dependency checks</summary>

- `uv run python -m unittest tests.warren_baseline.test_build_baseline tests.warren_baseline.test_repository tests.warren_baseline.test_schema tests.warren_baseline.test_api`: 15 passed.
- `web/npm run build`: passed.
- `web/npm run lint`: 12 errors and 8 warnings outside the active baseline directory; baseline files produced no diagnostics.
</details>
