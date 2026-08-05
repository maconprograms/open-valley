"""Characterization tests for the strictly redacted public release bundle."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from src.warren_baseline.schema import SourceRun


def synthetic_records() -> dict[str, list[dict]]:
    retrieved_at = "2026-08-04T12:00:00Z"
    nemrc_source = {
        "source_run_id": "warren-synthetic",
        "source_key": "nemrc:001",
        "source_url": "https://example.test/assessment?prop=001",
        "source_extract": "private-joined.csv",
        "source_fields": ["parcel_id", "owner", "location"],
        "retrieved_at": retrieved_at,
    }
    vcgi_source = {
        "source_run_id": "warren-synthetic",
        "source_key": "vcgi:100",
        "source_url": "https://example.test/cadastral/FeatureServer/0",
        "source_extract": "private-parcels.geojson",
        "source_fields": ["PARCID", "HSDECL", "GLYEAR"],
        "retrieved_at": retrieved_at,
    }
    return {
        "source_records": [
            {
                "id": "source:one",
                "source": nemrc_source,
                "raw_values": {"owner": "Private Test Owner", "mailing": "CA"},
            }
        ],
        "property_accounts": [
            {
                "id": "warren:001",
                "town": "Warren",
                "address": "1 Public Road",
                "source": nemrc_source,
            }
        ],
        "parcel_geometries": [
            {
                "id": "geometry:warren:001",
                "account_id": "warren:001",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[-72.0, 44.0], [-72.1, 44.0], [-72.0, 44.0]]],
                },
                "link_confidence": "exact_parcid",
                "source": vcgi_source,
            }
        ],
        "assessment_snapshots": [
            {
                "id": "assessment:warren:001:2026",
                "account_id": "warren:001",
                "grand_list_year": 2026,
                "homestead_filed": True,
                "source": vcgi_source,
            }
        ],
        "housing_unit_claims": [
            {
                "id": "unit:warren:001:1",
                "account_id": "warren:001",
                "evidence_level": "documented",
                "source": vcgi_source,
            }
        ],
        "ownership_observations": [
            {
                "id": "ownership:warren:001:1",
                "account_id": "warren:001",
                "owner_text": "Private Test Owner",
                "mailing_address": "99 Private Lane",
                "mailing_state": "CA",
                "source": nemrc_source,
            }
        ],
    }


class PublicReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.now = datetime(2026, 8, 5, tzinfo=UTC)
        self.run = SourceRun(
            id="warren-synthetic",
            town="Warren",
            retrieved_at=datetime(2026, 8, 4, 12, tzinfo=UTC),
            status="validated",
            parser_version="test-v1",
            input_checksums={"private-input.csv": "abc"},
            coverage={"accounts": 1},
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_export_creates_a_complete_strictly_redacted_bundle(self):
        from src.warren_baseline.public_release import export_public_release

        receipt = export_public_release(
            self.run, synthetic_records(), self.root, now=self.now
        )

        release_directory = self.root / "warren" / receipt.release_id
        self.assertTrue((release_directory / "manifest.json").is_file())
        self.assertTrue((release_directory / "summary.json").is_file())
        self.assertTrue((release_directory / "homestead-trend.json").is_file())
        self.assertTrue((release_directory / "providers.json").is_file())
        self.assertTrue((release_directory / "map.geojson").is_file())
        self.assertEqual(
            json.loads((self.root / "warren" / "current.json").read_text())["release_id"],
            receipt.release_id,
        )

        map_payload = json.loads((release_directory / "map.geojson").read_text())
        properties = map_payload["features"][0]["properties"]
        self.assertEqual(properties["address"], "1 Public Road")
        self.assertEqual(properties["tax_status_bucket"], "homestead_filed")
        self.assertNotIn("account_id", properties)
        rendered = (release_directory / "map.geojson").read_text()
        self.assertNotIn("Private Test Owner", rendered)
        self.assertNotIn("99 Private Lane", rendered)
        self.assertNotIn("mailing_state", rendered)

        providers = json.loads((release_directory / "providers.json").read_text())
        self.assertEqual(providers["providers"][0]["provider_url"], "https://example.test/")
        self.assertNotIn("source_extract", repr(providers))
        self.assertNotIn("source_key", repr(providers))

    def test_provider_descriptor_rejects_private_locators_and_unknown_nested_fields(self):
        from src.warren_baseline.public_schema import PublicProviderDescriptor
        from pydantic import ValidationError

        payload = {
            "provider": "nemrc",
            "provider_url": "https://example.test/assessment?prop=001",
            "retrieved_at": "2026-08-04T12:00:00Z",
            "retrieved_timezone": "UTC",
            "aggregate_checksum": "abc",
            "field_labels": ["location"],
            "raw_filename": "private.csv",
        }
        with self.assertRaises(ValidationError):
            PublicProviderDescriptor.model_validate(payload)

        property_url_payload = {
            **payload,
            "provider_url": "https://example.test/property/001",
            "aggregate_checksum": "a" * 64,
        }
        property_url_payload.pop("raw_filename")
        with self.assertRaises(ValidationError):
            PublicProviderDescriptor.model_validate(property_url_payload)

    def test_unsafe_output_does_not_promote_or_replace_the_current_pointer(self):
        from src.warren_baseline.public_release import (
            PublicReleaseSafetyError,
            export_public_release,
        )

        safe = export_public_release(self.run, synthetic_records(), self.root, now=self.now)
        unsafe_records = synthetic_records()
        unsafe_records["property_accounts"][0]["address"] = "Private Test Owner"
        with self.assertRaisesRegex(PublicReleaseSafetyError, "map.geojson.*address") as error:
            export_public_release(
                self.run.model_copy(update={"id": "warren-unsafe"}),
                unsafe_records,
                self.root,
                now=self.now,
            )

        self.assertNotIn("Private Test Owner", str(error.exception))
        pointer = json.loads((self.root / "warren" / "current.json").read_text())
        self.assertEqual(pointer["release_id"], safe.release_id)
        self.assertFalse((self.root / "warren" / "warren-unsafe--v1").exists())

    def test_canonical_provenance_values_do_not_trigger_private_value_scan(self):
        from src.warren_baseline.public_release import (
            PublicReleaseSafetyError,
            scan_public_artifact,
        )

        scan_public_artifact(
            {"town": "Warren", "release_version": "v1"},
            "summary.json",
            {"warren"},
        )
        with self.assertRaises(PublicReleaseSafetyError):
            scan_public_artifact(
                {"address": "Private Test Owner"},
                "map.geojson",
                {"private test owner"},
            )

    def test_unvalidated_or_insufficiently_covered_runs_cannot_export(self):
        from src.warren_baseline.public_release import PublicReleaseError, export_public_release

        with self.assertRaisesRegex(PublicReleaseError, "validated"):
            export_public_release(
                self.run.model_copy(update={"status": "staged"}),
                synthetic_records(),
                self.root,
                now=self.now,
            )

        incomplete = synthetic_records()
        incomplete["assessment_snapshots"][0]["homestead_filed"] = None
        with self.assertRaisesRegex(PublicReleaseError, "coverage"):
            export_public_release(self.run, incomplete, self.root, now=self.now)

    def test_stale_source_run_cannot_export_without_a_public_stale_notice(self):
        from src.warren_baseline.public_release import PublicReleaseError, export_public_release

        stale = self.run.model_copy(
            update={"retrieved_at": self.now - timedelta(days=91)}
        )
        with self.assertRaisesRegex(PublicReleaseError, "stale"):
            export_public_release(stale, synthetic_records(), self.root, now=self.now)


if __name__ == "__main__":
    unittest.main()
