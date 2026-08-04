import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from warren.scripts.build_baseline import materialize_baseline

from .test_build_baseline import BuildBaselineTests


class BaselineRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        fixture = BuildBaselineTests()
        self.result = materialize_baseline(
            joined_path=fixture.write_joined(self.root),
            parcels_path=fixture.write_geojson(self.root),
            output_root=self.root / "baseline",
            retrieved_at=datetime(2026, 8, 3, tzinfo=UTC),
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_promotion_writes_a_privacy_preserving_map_projection(self):
        from src.warren_baseline.repository import BaselineRepository

        repository = BaselineRepository(self.root / "baseline")
        repository.promote(self.result.run_id)

        projection = repository.map_projection()
        self.assertEqual(projection["source_run_id"], self.result.run_id)
        self.assertEqual(len(projection["features"]), 1)
        properties = projection["features"][0]["properties"]
        self.assertEqual(properties["homestead_filed"], False)
        self.assertEqual(properties["mailing_state"], "MA")
        self.assertTrue(properties["out_of_state_mailing"])
        self.assertNotIn("owner_text", properties)
        self.assertNotIn("mailing_address", properties)

    def test_summary_keeps_denominators_and_unknowns_explicit(self):
        from src.warren_baseline.repository import BaselineRepository

        repository = BaselineRepository(self.root / "baseline")
        repository.promote(self.result.run_id)

        summary = repository.summary()
        self.assertEqual(summary["tax_accounts"]["total"], 1)
        self.assertEqual(summary["homestead_filed"]["no"], 1)
        self.assertEqual(summary["out_of_state_mailing"]["yes"], 1)
        self.assertEqual(summary["housing_unit_claims"]["total"], 2)


if __name__ == "__main__":
    unittest.main()
