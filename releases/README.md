# Public releases

This directory contains only versioned, redacted Open Valley release bundles.
Each town has a `current.json` pointer and immutable artifact directories.

Public bundles include map-safe property addresses and geometry, aggregate
homestead-filing observations, coverage, and provider-level provenance. They
never include owner, mailing, review, raw source-record, or private-storage data.

An operator exports a validated private ledger run with:

```sh
uv run python warren/scripts/export_public_release.py --town Warren --source-run RUN_ID
```

The export validates every artifact against strict allowlist schemas and scans
it before moving the current pointer. The command must run only in an operator
environment with private database access.
