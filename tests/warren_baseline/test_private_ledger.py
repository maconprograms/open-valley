import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from src.warren_baseline.schema import SourceRun
from warren.scripts.build_baseline import import_materialized_run


class RecordingCursor:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, query, params=None):
        self.connection.statements.append((" ".join(query.split()), params))

    def executemany(self, query, params):
        self.connection.statements.append((" ".join(query.split()), list(params)))

    def fetchall(self):
        return self.connection.rows.pop(0) if self.connection.rows else []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class RecordingConnection:
    def __init__(self, rows=None):
        self.rows = list(rows or [])
        self.statements = []
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return RecordingCursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class PrivateLedgerTests(unittest.TestCase):
    def source_run(self, town="Warren"):
        return SourceRun(
            id="warren-synthetic",
            town=town,
            retrieved_at=datetime(2026, 8, 4, tzinfo=UTC),
            status="validated",
            input_checksums={"joined": "abc"},
            coverage={"accounts": 1},
        )

    def test_migration_creates_append_only_town_keyed_tables(self):
        from src.warren_baseline.private_ledger import PrivateLedger

        connection = RecordingConnection()
        PrivateLedger(connection).migrate()

        statements = "\n".join(statement for statement, _ in connection.statements)
        self.assertIn("CREATE TABLE IF NOT EXISTS private_source_runs", statements)
        self.assertIn("CREATE TABLE IF NOT EXISTS private_ledger_records", statements)
        self.assertIn("CREATE TABLE IF NOT EXISTS private_human_reviews", statements)
        self.assertIn("town TEXT NOT NULL", statements)
        self.assertIn("private_ledger_forbid_mutation", statements)
        self.assertIn("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC", statements)
        self.assertEqual(connection.commits, 1)

    def test_import_keeps_raw_records_run_scoped_and_town_scoped(self):
        from src.warren_baseline.private_ledger import PrivateLedger

        connection = RecordingConnection()
        result = PrivateLedger(connection).import_run(
            self.source_run(),
            {
                "source_records": [{"id": "source:one", "raw_values": {"owner": "Synthetic"}}],
                "ownership_observations": [{"id": "ownership:one", "owner_text": "Synthetic"}],
                "assessment_snapshots": [{"id": "assessment:one", "account_id": "warren:1"}],
            },
            reviews=[
                {
                    "id": "review:one",
                    "account_id": "warren:1",
                    "source_run_id": "warren-synthetic",
                    "note": "Synthetic",
                }
            ],
        )

        self.assertEqual(result.record_counts["source_records"], 1)
        self.assertEqual(result.record_counts["ownership_observations"], 1)
        self.assertEqual(result.review_count, 1)
        inserts = [
            params for statement, params in connection.statements if "INSERT INTO" in statement
        ]
        flattened = repr(inserts)
        self.assertIn("warren-synthetic", flattened)
        self.assertIn("Warren", flattened)
        self.assertEqual(connection.commits, 1)

    def test_invalid_record_rolls_back_without_validating_run(self):
        from src.warren_baseline.private_ledger import PrivateLedger, PrivateLedgerError

        connection = RecordingConnection()
        with self.assertRaisesRegex(PrivateLedgerError, "invalid private ledger input"):
            PrivateLedger(connection).import_run(
                self.source_run(), {"source_records": [{"raw_values": {"owner": "Synthetic"}}]}
            )

        statements = "\n".join(statement for statement, _ in connection.statements)
        self.assertNotIn("INSERT INTO private_source_runs", statements)
        self.assertEqual(connection.rollbacks, 0)

    def test_staged_run_is_rejected_before_any_write(self):
        from src.warren_baseline.private_ledger import PrivateLedger, PrivateLedgerError

        connection = RecordingConnection()
        staged_run = self.source_run().model_copy(update={"status": "staged"})
        with self.assertRaisesRegex(PrivateLedgerError, "invalid private ledger input"):
            PrivateLedger(connection).import_run(staged_run, {})

        self.assertEqual(connection.statements, [])

    def test_review_cannot_be_imported_under_a_different_source_run(self):
        from src.warren_baseline.private_ledger import PrivateLedger, PrivateLedgerError

        connection = RecordingConnection()
        with self.assertRaisesRegex(PrivateLedgerError, "invalid private ledger input"):
            PrivateLedger(connection).import_run(
                self.source_run(),
                {},
                reviews=[{"id": "review:one", "source_run_id": "different-run"}],
            )

        self.assertEqual(connection.statements, [])

    def test_second_town_isolated_from_warren_run_reads(self):
        from src.warren_baseline.private_ledger import PrivateLedger

        connection = RecordingConnection(
            rows=[[("source:one", "source_records", {"id": "source:one"})]]
        )
        records = PrivateLedger(connection).read_run_records("warren-synthetic", "Warren")

        self.assertEqual(records["source_records"][0]["id"], "source:one")
        query, params = connection.statements[-1]
        self.assertIn("WHERE source_run_id = %s AND town = %s", query)
        self.assertEqual(params, ("warren-synthetic", "Warren"))

    def test_public_container_configuration_cannot_get_private_database_url(self):
        from src.warren_baseline.private_ledger import (
            PrivateLedgerConfigurationError,
            private_database_url,
        )

        with self.assertRaisesRegex(PrivateLedgerConfigurationError, "not available"):
            private_database_url(
                {
                    "OPENVALLEY_RUNTIME": "public",
                    "OPENVALLEY_PRIVATE_DATABASE_URL": "postgresql://private",
                }
            )

        with self.assertRaisesRegex(PrivateLedgerConfigurationError, "not configured"):
            private_database_url({"OPENVALLEY_RUNTIME": "operator"})

    def test_import_directory_uses_only_known_run_artifacts(self):
        from src.warren_baseline.private_ledger import load_private_run_directory

        with tempfile.TemporaryDirectory() as temporary_directory:
            run_directory = Path(temporary_directory)
            run_directory.joinpath("source_run.json").write_text(
                json.dumps(self.source_run().model_dump(mode="json")), encoding="utf-8"
            )
            run_directory.joinpath("source_records.jsonl").write_text(
                '{"id":"source:one","raw_values":{"owner":"Synthetic"}}\n', encoding="utf-8"
            )
            run, records = load_private_run_directory(run_directory)

        self.assertEqual(run.id, "warren-synthetic")
        self.assertEqual(records["source_records"][0]["id"], "source:one")

    def test_materializer_import_helper_keeps_database_access_operator_supplied(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            run_directory = root / "runs" / "warren-synthetic"
            run_directory.mkdir(parents=True)
            run_directory.joinpath("source_run.json").write_text(
                json.dumps(self.source_run().model_dump(mode="json")), encoding="utf-8"
            )
            run_directory.joinpath("source_records.jsonl").write_text(
                '{"id":"source:one","raw_values":{"owner":"Synthetic"}}\n', encoding="utf-8"
            )
            ledger = type("Ledger", (), {"import_run": lambda _, run, records: (run.id, records)})()
            imported_run_id, records = import_materialized_run(root, "warren-synthetic", ledger)

        self.assertEqual(imported_run_id, "warren-synthetic")
        self.assertEqual(records["source_records"][0]["id"], "source:one")


if __name__ == "__main__":
    unittest.main()
