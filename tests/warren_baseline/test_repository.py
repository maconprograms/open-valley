"""Tests for the public-release-only repository."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path


def write_public_release(root: Path) -> Path:
    """Write a schema-valid redacted release fixture with no private ledger."""

    from src.warren_baseline.public_release import export_public_release
    from src.warren_baseline.schema import SourceRun

    retrieved_at = "2026-08-04T12:00:00Z"
    source = {
        "source_run_id": "warren-public-fixture",
        "source_key": "vcgi:collection",
        "source_url": "https://example.test/",
        "source_fields": ["HSDECL", "PARCID"],
        "retrieved_at": retrieved_at,
    }
    run = SourceRun(
        id="warren-public-fixture",
        town="Warren",
        retrieved_at=datetime(2026, 8, 4, 12, tzinfo=UTC),
        status="validated",
        parser_version="test-v1",
        input_checksums={"private-input.csv": "abc"},
        coverage={"accounts": 1},
    )
    records = {
        "source_records": [{"id": "source:one", "source": source, "raw_values": {}}],
        "property_accounts": [
            {"id": "warren:001", "town": "Warren", "address": "1 Public Road", "source": source}
        ],
        "parcel_geometries": [
            {
                "id": "geometry:warren:001",
                "account_id": "warren:001",
                "geometry": {"type": "Polygon", "coordinates": [[[-72.0, 44.0], [-72.1, 44.0], [-72.0, 44.0]]]},
                "link_confidence": "exact_parcid",
                "source": source,
            }
        ],
        "assessment_snapshots": [
            {
                "id": "assessment:warren:001:2026",
                "account_id": "warren:001",
                "grand_list_year": 2026,
                "homestead_filed": True,
                "source": source,
            }
        ],
        "housing_unit_claims": [
            {"id": "unit:warren:001:1", "account_id": "warren:001", "evidence_level": "documented", "source": source}
        ],
    }
    export_public_release(run, records, root, now=datetime(2026, 8, 5, tzinfo=UTC))
    return root


class PublicReleaseRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = write_public_release(Path(self.temporary_directory.name))

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_reads_only_allowlisted_release_artifacts(self):
        from src.warren_baseline.repository import PublicReleaseRepository

        repository = PublicReleaseRepository(self.root)

        self.assertEqual(repository.summary()["town"], "Warren")
        self.assertEqual(repository.homestead_trend()["observations"][0]["grand_list_year"], 2026)
        self.assertEqual(repository.providers()["providers"][0]["provider"], "vcgi")
        self.assertEqual(repository.map_projection()["features"][0]["properties"]["address"], "1 Public Road")
        self.assertNotIn("owner_text", repository.map_projection()["features"][0]["properties"])

    def test_health_validates_pointer_and_every_required_artifact(self):
        from src.warren_baseline.repository import PublicReleaseRepository

        repository = PublicReleaseRepository(self.root)
        self.assertEqual(repository.health()["status"], "ok")

        pointer = self.root / "warren" / "current.json"
        release_id = json.loads(pointer.read_text(encoding="utf-8"))["release_id"]
        (self.root / "warren" / release_id / "providers.json").unlink()

        with self.assertRaisesRegex(Exception, "unavailable"):
            repository.health()

    def test_missing_or_invalid_pointer_fails_without_paths_or_payloads(self):
        from src.warren_baseline.repository import PublicReleaseRepository, PublicReleaseUnavailableError

        repository = PublicReleaseRepository(self.root)
        (self.root / "warren" / "current.json").write_text("{not json", encoding="utf-8")

        with self.assertRaises(PublicReleaseUnavailableError) as error:
            repository.summary()
        self.assertEqual(str(error.exception), "public release unavailable")
        self.assertNotIn(str(self.root), str(error.exception))


if __name__ == "__main__":
    unittest.main()
