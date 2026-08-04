import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.warren_baseline.api import create_baseline_router
from src.warren_baseline.repository import BaselineRepository
from warren.scripts.build_baseline import materialize_baseline

from .test_build_baseline import BuildBaselineTests


class BaselineApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        fixture = BuildBaselineTests()
        result = materialize_baseline(
            joined_path=fixture.write_joined(root),
            parcels_path=fixture.write_geojson(root),
            output_root=root / "baseline",
            retrieved_at=datetime(2026, 8, 3, tzinfo=UTC),
        )
        repository = BaselineRepository(root / "baseline", root / "reviews")
        repository.promote(result.run_id)
        app = FastAPI()
        app.include_router(create_baseline_router(repository))
        self.client = TestClient(app)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_baseline_endpoints_expose_facts_and_lineage(self):
        summary = self.client.get("/api/baseline/summary")
        map_data = self.client.get("/api/baseline/map")
        detail = self.client.get("/api/baseline/accounts/warren:0010001")
        sources = self.client.get("/api/baseline/sources")

        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.json()["tax_accounts"]["total"], 1)
        self.assertEqual(map_data.status_code, 200)
        self.assertTrue(map_data.headers["content-type"].startswith("application/geo+json"))
        self.assertNotIn("owner_text", map_data.json()["features"][0]["properties"])
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(
            detail.json()["review_status_by_subject"]["homestead_filing"], "unreviewed"
        )
        ownership = detail.json()["ownership_observations"]
        self.assertEqual(ownership[0]["owner_text"], "CARTER PATRICIA SUE")
        self.assertEqual(sources.status_code, 200)
        self.assertEqual(sources.json()["source_run"]["town"], "Warren")

    def test_unknown_account_returns_not_found(self):
        response = self.client.get("/api/baseline/accounts/warren:missing")
        self.assertEqual(response.status_code, 404)

    def test_review_queue_is_not_part_of_the_public_api(self):
        response = self.client.get("/api/baseline/review-queue")
        self.assertEqual(response.status_code, 404)

    def test_standalone_app_serves_the_materialized_homestead_trend(self):
        from src.warren_baseline.app import app

        response = TestClient(app).get("/api/baseline/trends/homestead")
        self.assertEqual(response.status_code, 200)
        observations = response.json()["observations"]
        self.assertEqual(observations[-1]["grand_list_year"], 2025)
        self.assertEqual(observations[-1]["homestead_filed"], 528)


if __name__ == "__main__":
    unittest.main()
