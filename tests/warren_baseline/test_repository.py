import json
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

    def test_promotion_writes_a_tax_status_only_map_projection(self):
        from src.warren_baseline.repository import BaselineRepository

        repository = BaselineRepository(self.root / "baseline", self.root / "reviews")
        repository.promote(self.result.run_id)

        projection = repository.map_projection()
        self.assertEqual(repository.map_projection_path().name, "map-tax-status-v1.geojson")
        self.assertEqual(projection["source_run_id"], self.result.run_id)
        self.assertEqual(len(projection["features"]), 1)
        properties = projection["features"][0]["properties"]
        self.assertEqual(properties["tax_status_bucket"], "non_homestead")
        self.assertNotIn("owner_text", properties)
        self.assertNotIn("mailing_address", properties)
        self.assertNotIn("mailing_state", properties)
        self.assertNotIn("out_of_state_mailing", properties)

    def test_summary_keeps_denominators_and_unknowns_explicit(self):
        from src.warren_baseline.repository import BaselineRepository

        repository = BaselineRepository(self.root / "baseline", self.root / "reviews")
        repository.promote(self.result.run_id)

        summary = repository.summary()
        self.assertEqual(summary["tax_accounts"]["total"], 1)
        self.assertEqual(summary["tax_status_buckets"]["non_homestead"], 1)
        self.assertNotIn("out_of_state_mailing", summary)
        self.assertEqual(summary["housing_unit_claims"]["total"], 2)

    def test_human_reviews_do_not_replace_source_observations(self):
        from src.warren_baseline.repository import BaselineRepository

        repository = BaselineRepository(self.root / "baseline", self.root / "reviews")
        repository.promote(self.result.run_id)
        repository.review_path.parent.mkdir(parents=True)
        repository.review_path.write_text(
            json.dumps(
                {
                    "id": "review:warren:0010001:mailing-address:2026-08-03",
                    "account_id": "warren:0010001",
                    "source_run_id": self.result.run_id,
                    "subject": "mailing_address",
                    "status": "contradicted",
                    "reviewed_at": "2026-08-03T12:00:00Z",
                    "reviewed_by": "test reviewer",
                    "evidence_summary": "The source mailing address is stale.",
                    "source_observation_ids": ["ownership:warren:0010001:1"],
                }
            )
            + "\n"
            + json.dumps(
                {
                    "id": "review:warren:0010001:homestead:previous-run",
                    "account_id": "warren:0010001",
                    "source_run_id": "warren-previous-run",
                    "subject": "homestead_filing",
                    "status": "confirmed",
                    "reviewed_at": "2026-08-02T12:00:00Z",
                    "reviewed_by": "test reviewer",
                    "evidence_summary": "This review applies only to an earlier source run.",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        detail = repository.account_detail("warren:0010001")
        self.assertEqual(detail["review_status_by_subject"]["mailing_address"], "contradicted")
        self.assertEqual(detail["review_status_by_subject"]["homestead_filing"], "unreviewed")
        self.assertEqual(detail["ownership_observations"][0]["mailing_state"], "MA")
        self.assertEqual(
            repository.review_queue()[0]["review_status_by_subject"]["mailing_address"],
            "contradicted",
        )
        self.assertNotIn("mailing_state", repository.map_projection()["features"][0]["properties"])

    def test_invalid_human_review_ledger_raises_a_controlled_error(self):
        from src.warren_baseline.repository import BaselineRepository, ReviewLedgerError

        repository = BaselineRepository(self.root / "baseline", self.root / "reviews")
        repository.promote(self.result.run_id)
        repository.review_path.parent.mkdir(parents=True)
        repository.review_path.write_text("not valid json\n", encoding="utf-8")

        with self.assertRaises(ReviewLedgerError):
            repository.account_detail("warren:0010001")


if __name__ == "__main__":
    unittest.main()
