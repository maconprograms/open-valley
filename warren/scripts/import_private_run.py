#!/usr/bin/env python3
"""Import one protected, materialized source run into the private ledger.

The input directory and database URL are operator-only. Output reports only
run-level counts and checksums; it never prints input paths or source values.
Remove the protected migration backup only after independently comparing this
receipt with that backup, then follow the protected-storage disposal policy.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src.warren_baseline.private_ledger import (
    PrivateLedger,
    PrivateLedgerError,
    connect_private_ledger,
    load_private_reviews,
    load_private_run_directory,
    private_database_url,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="protected source-run directory")
    parser.add_argument("--reviews", type=Path, help="optional protected review JSONL")
    args = parser.parse_args()
    try:
        source_run, records = load_private_run_directory(args.input)
        reviews = load_private_reviews(args.reviews)
        connection = connect_private_ledger(private_database_url())
        receipt = PrivateLedger(connection).import_run(source_run, records, reviews=reviews)
    except PrivateLedgerError as error:
        raise SystemExit(str(error)) from error
    print(
        "private run validated: "
        f"town={receipt.town} run={receipt.source_run_id} "
        f"records={sum(receipt.record_counts.values())} reviews={receipt.review_count}"
    )


if __name__ == "__main__":
    main()
