#!/usr/bin/env python3
"""Export one validated private source run as a redacted public bundle."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.warren_baseline.private_ledger import (
    PrivateLedger,
    PrivateLedgerError,
    connect_private_ledger,
    private_database_url,
)
from src.warren_baseline.public_release import PublicReleaseError, export_public_release


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--town", required=True)
    parser.add_argument("--source-run", required=True)
    parser.add_argument("--releases-root", default="releases")
    args = parser.parse_args()
    try:
        with connect_private_ledger(private_database_url()) as connection:
            ledger = PrivateLedger(connection)
            run = ledger.read_source_run(args.source_run, args.town)
            records = ledger.read_run_records(args.source_run, args.town)
        receipt = export_public_release(run, records, Path(args.releases_root))
    except (PrivateLedgerError, PublicReleaseError):
        print("public release export failed")
        return 1
    print(f"exported redacted release {receipt.release_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
