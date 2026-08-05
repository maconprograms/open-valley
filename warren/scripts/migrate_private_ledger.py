#!/usr/bin/env python3
"""Create private-ledger tables in the protected operator Postgres service.

This command reads ``OPENVALLEY_PRIVATE_DATABASE_URL`` only in an operator
runtime. Never run it from a public application container or record its output
with connection details.
"""

from src.warren_baseline.private_ledger import (
    PrivateLedger,
    PrivateLedgerError,
    connect_private_ledger,
    private_database_url,
)


def main() -> None:
    try:
        connection = connect_private_ledger(private_database_url())
        PrivateLedger(connection).migrate()
    except PrivateLedgerError as error:
        raise SystemExit(str(error)) from error
    print("private ledger migration completed")


if __name__ == "__main__":
    main()
