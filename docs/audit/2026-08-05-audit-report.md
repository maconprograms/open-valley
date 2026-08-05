# Codebase Audit Report — Open Valley

**Date:** 2026-08-05  
**Scope:** Public-release boundary and Warren frontend  
**Stack:** FastAPI/Pydantic, Next.js/React, MapLibre, versioned JSON/GeoJSON releases  
**Previous audit:** First audit  
**Framework guidance consulted:** uv `llms.txt`; FastAPI and Pydantic retrieval was unavailable.

## Executive summary

The deployed runtime has a strong release-only boundary, but the repository does not
yet meet its own public-history promise: two removed artifacts remain reachable in
`origin/main`, and a name-like fixture is committed. The public UI also renders a
3,003-option native select, which is technically focusable but impractical for real
keyboard and assistive-technology use.

**Findings:** 2 Critical, 5 Significant, 4 Cleanup  
**Punchlist items:** 11

## Remediation status

This audit was completed before the fixes in the accompanying change. The
oversized selector, linear parcel lookup, provenance field vocabulary,
mailing-address safeguard, typography cleanup, and duplicate metadata have
been addressed. The history rewrite and the map-delivery improvements remain
the release-critical follow-through.

## Metrics

| Metric | Value |
| --- | ---: |
| Application source files reviewed | 43 |
| Frontend tests | 4 |
| Backend tests | 33 |
| TODO/FIXME/HACK markers | 0 |
| Raw-history findings | 2 paths |
| Largest public UI payload observed | 15.15 MB GeoJSON |

## Punchlist

1. **[CRITICAL]** Rewrite reachable public history for the two removed `data/` artifacts and request GitHub cached-object purge. `scripts/check_public_tree.py:114-152` checks only the checkout, while `git rev-list origin/main -- <path>` still returns both historical paths.
2. **[CRITICAL]** Replace the name-like owner fixture with an unmistakably synthetic value and include that path in the same history remediation. `tests/warren_baseline/test_schema.py:73-89`.
3. **[SIGNIFICANT]** Replace free-form provenance field labels with a fixed public vocabulary or omit them. `src/warren_baseline/public_release.py:260-299` currently publishes upstream owner, mailing, buyer, and seller field names.
4. **[SIGNIFICANT]** Require explicit property-location provenance before exempting an address from the protected-value scan. `src/warren_baseline/public_release.py:186-195,439-441`.
5. **[SIGNIFICANT]** Replace the 3,003-option parcel select with a labelled, capped address-search result list. `web/src/components/baseline/BaselineMap.tsx:221-235`.
6. **[SIGNIFICANT]** Move full-map validation/caching out of the per-visitor hot path and eventually split address search from map geometry. `src/warren_baseline/repository.py:99`; `web/src/components/baseline/BaselineMap.tsx:85-122`.
7. **[SIGNIFICANT]** Document or replace the direct third-party CARTO basemap dependency and add a distinct basemap failure state. `web/src/components/baseline/BaselineMap.tsx:111-116`.
8. **[CLEANUP]** Index parcels by selection key instead of linearly scanning them on pointer movement and selection. `web/src/components/baseline/BaselineMap.tsx:141-145,171-176`.
9. **[CLEANUP]** Remove the unused typography plugin. `web/src/app/globals.css:2`; `web/package.json`.
10. **[CLEANUP]** Resolve the loaded Geist font versus Arial body-font conflict and deduplicate page metadata. `web/src/app/layout.tsx:5-18`; `web/src/app/page.tsx:3-6`; `web/src/app/globals.css:23-26`.
11. **[CLEANUP]** Update the README’s now-stale pre-launch history status. `README.md:40-45`.

## Why the top findings matter

### Public history is a release boundary, not just a working-tree concern

The current guard correctly rejects unsafe files in the checked-out tree, but Git
objects reachable from a public branch can still be fetched by commit ID. A public
release needs both a clean checkout and clean reachable refs. The fix is a targeted
history rewrite, force-push of every public ref, GitHub cache-purge request, and a
CI history scan that reports only paths—not values.

### A focusable control can still be inaccessible at real scale

A native select is semantically valid, but 3,003 options make discovery, keyboard
navigation, and screen-reader output unusable. A labelled search input that renders
only a small set of matching public-address buttons preserves a keyboard alternative
without putting thousands of DOM nodes behind one control.

## What is working well

- `src/warren_baseline/public_schema.py:21-25` uses strict, fail-closed public models.
- `src/warren_baseline/app.py:9-20` and `Dockerfile.api:12-30` keep the public runtime on release artifacts, not the private ledger.
- `web/src/components/baseline/BaselineDashboard.tsx:90-145` uses real sections, headings, tables, and plain-language limits beside the data.
- `scripts/check_public_tree.py:114-157` intentionally reports paths and fields rather than rejected values.

## Audit method

Three independent, report-only reviews covered accessibility/performance,
privacy/security, and hygiene/test quality. Findings were deduplicated and verified
against the local checkout and reachable `origin/main` history before this report was
written. No private values are repeated here.
