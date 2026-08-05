"""Private, append-only Postgres storage for raw Open Valley source runs.

This module is intentionally not imported by the public API.  It is available
only to operator-run import and export processes with private database access.
Errors are deliberately data-free: callers must not log raw inputs, paths,
connection strings, or database exception text.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from pydantic import ValidationError

from .schema import SourceRun

PRIVATE_RECORD_TYPES = (
    "source_records",
    "property_accounts",
    "parcel_geometries",
    "housing_unit_claims",
    "assessment_snapshots",
    "ownership_observations",
    "normalized_party_matches",
    "transfer_events",
)
PRIVATE_REVIEW_FILENAME = "human_reviews.jsonl"


class PrivateLedgerError(RuntimeError):
    """A private-ledger operation failed without exposing source data."""


class PrivateLedgerConfigurationError(PrivateLedgerError):
    """Private database access was requested from an unsafe runtime."""


class Cursor(Protocol):
    def execute(self, query: str, params: Sequence[Any] | None = None) -> Any: ...

    def executemany(self, query: str, params: Sequence[Sequence[Any]]) -> Any: ...

    def fetchall(self) -> list[tuple[Any, ...]]: ...

    def __enter__(self) -> "Cursor": ...

    def __exit__(self, *args: Any) -> bool | None: ...


class Connection(Protocol):
    def cursor(self) -> Cursor: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


@dataclass(frozen=True)
class PrivateImportReceipt:
    """Safe import-validation facts; intentionally excludes raw values."""

    source_run_id: str
    town: str
    record_counts: dict[str, int]
    review_count: int
    input_checksums: dict[str, str]


def private_database_url(environment: Mapping[str, str] | None = None) -> str:
    """Read an operator-only URL while rejecting any public runtime.

    The URL itself is never included in an exception or log message.
    """

    environment = environment if environment is not None else os.environ
    if (
        environment.get("OPENVALLEY_RUNTIME") == "public"
        or environment.get("OPENVALLEY_PUBLIC_CONTAINER") == "1"
    ):
        raise PrivateLedgerConfigurationError(
            "private database access is not available in public runtime"
        )
    database_url = environment.get("OPENVALLEY_PRIVATE_DATABASE_URL")
    if not database_url:
        raise PrivateLedgerConfigurationError("private database is not configured")
    return database_url


def connect_private_ledger(database_url: str) -> Connection:
    """Open an operator-only Postgres connection without leaking its target."""

    try:
        import psycopg

        return psycopg.connect(database_url)
    except Exception as error:  # pragma: no cover - requires an operator database
        raise PrivateLedgerError("private database connection failed") from error


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _payload_checksum(records: Sequence[Mapping[str, Any]]) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(_canonical_json(record).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _validate_records(records_by_type: Mapping[str, Sequence[Mapping[str, Any]]]) -> None:
    unknown_types = set(records_by_type) - set(PRIVATE_RECORD_TYPES)
    if unknown_types:
        raise PrivateLedgerError("invalid private ledger input")
    for record_type, records in records_by_type.items():
        if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
            raise PrivateLedgerError("invalid private ledger input")
        for record in records:
            if not isinstance(record, Mapping) or not isinstance(record.get("id"), str):
                raise PrivateLedgerError("invalid private ledger input")
            try:
                _canonical_json(record)
            except (TypeError, ValueError) as error:
                raise PrivateLedgerError("invalid private ledger input") from error


def _validate_reviews(
    reviews: Sequence[Mapping[str, Any]], source_run_id: str | None = None
) -> None:
    for review in reviews:
        if not isinstance(review, Mapping) or not isinstance(review.get("id"), str):
            raise PrivateLedgerError("invalid private ledger input")
        if source_run_id is not None and review.get("source_run_id") != source_run_id:
            raise PrivateLedgerError("invalid private ledger input")
        try:
            _canonical_json(review)
        except (TypeError, ValueError) as error:
            raise PrivateLedgerError("invalid private ledger input") from error


class PrivateLedger:
    """A transaction-scoped adapter for the protected raw source ledger."""

    def __init__(self, connection: Connection):
        self.connection = connection

    def migrate(self) -> None:
        """Create private tables and deny ambient public-schema access.

        Deploy this only on the separate protected Postgres service. Operator
        roles, encrypted backups, and credential rotation are provisioned
        outside this application and must not be added to public Compose files.
        """

        statements = (
            """
            CREATE TABLE IF NOT EXISTS private_source_runs (
                id TEXT NOT NULL,
                town TEXT NOT NULL,
                retrieved_at TIMESTAMPTZ NOT NULL,
                status TEXT NOT NULL CHECK (
                    status IN ('staged', 'validated', 'promoted', 'failed')
                ),
                parser_version TEXT NOT NULL,
                input_checksums JSONB NOT NULL,
                coverage JSONB NOT NULL,
                source_effective_date DATE,
                completed_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (town, id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS private_ledger_records (
                town TEXT NOT NULL,
                source_run_id TEXT NOT NULL,
                record_type TEXT NOT NULL,
                record_id TEXT NOT NULL,
                payload JSONB NOT NULL,
                payload_checksum TEXT NOT NULL,
                recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (town, source_run_id, record_type, record_id),
                FOREIGN KEY (town, source_run_id) REFERENCES private_source_runs(town, id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS private_human_reviews (
                town TEXT NOT NULL,
                source_run_id TEXT NOT NULL,
                review_id TEXT NOT NULL,
                payload JSONB NOT NULL,
                payload_checksum TEXT NOT NULL,
                recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (town, source_run_id, review_id),
                FOREIGN KEY (town, source_run_id) REFERENCES private_source_runs(town, id)
            )
            """,
            """
            CREATE OR REPLACE FUNCTION private_ledger_forbid_mutation()
            RETURNS TRIGGER AS $$
            BEGIN
                RAISE EXCEPTION 'private ledger records are append-only';
            END;
            $$ LANGUAGE plpgsql
            """,
            "DROP TRIGGER IF EXISTS private_source_runs_no_mutation ON private_source_runs",
            """
            CREATE TRIGGER private_source_runs_no_mutation
            BEFORE UPDATE OR DELETE ON private_source_runs
            FOR EACH ROW EXECUTE FUNCTION private_ledger_forbid_mutation()
            """,
            "DROP TRIGGER IF EXISTS private_ledger_records_no_mutation ON private_ledger_records",
            """
            CREATE TRIGGER private_ledger_records_no_mutation
            BEFORE UPDATE OR DELETE ON private_ledger_records
            FOR EACH ROW EXECUTE FUNCTION private_ledger_forbid_mutation()
            """,
            "DROP TRIGGER IF EXISTS private_human_reviews_no_mutation ON private_human_reviews",
            """
            CREATE TRIGGER private_human_reviews_no_mutation
            BEFORE UPDATE OR DELETE ON private_human_reviews
            FOR EACH ROW EXECUTE FUNCTION private_ledger_forbid_mutation()
            """,
            """
            CREATE INDEX IF NOT EXISTS private_ledger_records_town_run_idx
            ON private_ledger_records (town, source_run_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS private_human_reviews_town_run_idx
            ON private_human_reviews (town, source_run_id)
            """,
            "REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC",
        )
        try:
            with self.connection.cursor() as cursor:
                for statement in statements:
                    cursor.execute(statement)
            self.connection.commit()
        except Exception as error:
            self.connection.rollback()
            raise PrivateLedgerError("private ledger migration failed") from error

    def import_run(
        self,
        source_run: SourceRun,
        records_by_type: Mapping[str, Sequence[Mapping[str, Any]]],
        *,
        reviews: Sequence[Mapping[str, Any]] = (),
    ) -> PrivateImportReceipt:
        """Append a complete, validated source run atomically.

        Validation occurs before any write. Existing identifiers are never
        overwritten, preserving append-only provenance.
        """

        if source_run.status not in {"validated", "promoted"}:
            raise PrivateLedgerError("invalid private ledger input")
        _validate_records(records_by_type)
        _validate_reviews(reviews, source_run.id)
        record_counts = {
            record_type: len(records) for record_type, records in records_by_type.items()
        }
        checksums = {
            record_type: _payload_checksum(records)
            for record_type, records in records_by_type.items()
        }
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO private_source_runs
                        (id, town, retrieved_at, status, parser_version, input_checksums, coverage,
                         source_effective_date, completed_at)
                    VALUES (%s, %s, %s, 'validated', %s, %s::jsonb, %s::jsonb, %s, %s)
                    """,
                    (
                        source_run.id,
                        source_run.town,
                        source_run.retrieved_at,
                        source_run.parser_version,
                        _canonical_json(source_run.input_checksums),
                        _canonical_json(source_run.coverage),
                        source_run.source_effective_date,
                        source_run.completed_at,
                    ),
                )
                for record_type, records in records_by_type.items():
                    cursor.executemany(
                        """
                        INSERT INTO private_ledger_records
                            (source_run_id, town, record_type, record_id, payload, payload_checksum)
                        VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                        """,
                        [
                            (
                                source_run.id,
                                source_run.town,
                                record_type,
                                record["id"],
                                _canonical_json(record),
                                hashlib.sha256(_canonical_json(record).encode("utf-8")).hexdigest(),
                            )
                            for record in records
                        ],
                    )
                cursor.executemany(
                    """
                    INSERT INTO private_human_reviews
                        (source_run_id, town, review_id, payload, payload_checksum)
                    VALUES (%s, %s, %s, %s::jsonb, %s)
                    """,
                    [
                        (
                            source_run.id,
                            source_run.town,
                            review["id"],
                            _canonical_json(review),
                            hashlib.sha256(_canonical_json(review).encode("utf-8")).hexdigest(),
                        )
                        for review in reviews
                    ],
                )
            self.connection.commit()
        except Exception as error:
            self.connection.rollback()
            raise PrivateLedgerError("private ledger import failed") from error
        return PrivateImportReceipt(
            source_run_id=source_run.id,
            town=source_run.town,
            record_counts=record_counts,
            review_count=len(reviews),
            input_checksums=checksums,
        )

    def read_run_records(self, source_run_id: str, town: str) -> dict[str, list[dict[str, Any]]]:
        """Read one town-scoped run for a protected operator/export process."""

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT record_id, record_type, payload
                    FROM private_ledger_records
                    WHERE source_run_id = %s AND town = %s
                    ORDER BY record_type, record_id
                    """,
                    (source_run_id, town),
                )
                rows = cursor.fetchall()
        except Exception as error:
            raise PrivateLedgerError("private ledger read failed") from error
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record_id, record_type, payload in rows:
            if isinstance(payload, str):
                payload = json.loads(payload)
            if not isinstance(payload, dict) or payload.get("id") != record_id:
                raise PrivateLedgerError("private ledger record validation failed")
            grouped[record_type].append(payload)
        return dict(grouped)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    except (OSError, json.JSONDecodeError) as error:
        raise PrivateLedgerError("invalid private ledger input") from error


def load_private_run_directory(
    run_directory: Path,
) -> tuple[SourceRun, dict[str, list[dict[str, Any]]]]:
    """Read only known, run-scoped private artifacts from a protected location."""

    try:
        source_run_payload = json.loads(
            (run_directory / "source_run.json").read_text(encoding="utf-8")
        )
        source_run = SourceRun.model_validate(source_run_payload)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        raise PrivateLedgerError("invalid private ledger input") from error

    records: dict[str, list[dict[str, Any]]] = {}
    for record_type in PRIVATE_RECORD_TYPES:
        artifact = run_directory / f"{record_type}.jsonl"
        if artifact.exists():
            records[record_type] = _read_jsonl(artifact)
    _validate_records(records)
    return source_run, records


def load_private_reviews(path: Path | None) -> list[dict[str, Any]]:
    """Load a protected review artifact when one has been explicitly supplied."""

    if path is None:
        return []
    reviews = _read_jsonl(path)
    _validate_reviews(reviews)
    return reviews
