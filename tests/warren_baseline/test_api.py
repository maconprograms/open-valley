import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.warren_baseline.app import create_app
from src.warren_baseline.repository import PublicReleaseRepository
from tests.warren_baseline.test_repository import write_public_release


class PublicBaselineApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = write_public_release(Path(self.temporary_directory.name))
        self.client = TestClient(create_app(PublicReleaseRepository(root)))

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_public_endpoints_return_only_release_artifacts(self):
        summary = self.client.get("/api/baseline/summary")
        map_data = self.client.get("/api/baseline/map")
        trend = self.client.get("/api/baseline/trends/homestead")
        providers = self.client.get("/api/baseline/providers")

        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.json()["town"], "Warren")
        self.assertEqual(map_data.status_code, 200)
        self.assertTrue(map_data.headers["content-type"].startswith("application/geo+json"))
        self.assertNotIn("owner_text", map_data.json()["features"][0]["properties"])
        self.assertEqual(trend.status_code, 200)
        self.assertEqual(providers.status_code, 200)
        self.assertEqual(providers.json()["providers"][0]["provider"], "vcgi")

    def test_former_private_routes_are_not_found(self):
        for path in (
            "/api/baseline/accounts/warren:001",
            "/api/baseline/review-queue",
            "/api/baseline/transfers",
            "/api/baseline/sources",
        ):
            self.assertEqual(self.client.get(path).status_code, 404)

    def test_missing_release_is_a_controlled_unavailable_response(self):
        root = Path(self.temporary_directory.name)
        (root / "warren" / "current.json").unlink()

        response = self.client.get("/api/baseline/summary")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Public release is unavailable."})
        self.assertNotIn(str(root), response.text)

    def test_health_reads_the_release_without_database_configuration(self):
        response = self.client.get("/healthz")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

        root = Path(self.temporary_directory.name)
        pointer = root / "warren" / "current.json"
        release_id = json.loads(pointer.read_text(encoding="utf-8"))["release_id"]
        (root / "warren" / release_id / "map.geojson").unlink()
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Public release is unavailable."})


if __name__ == "__main__":
    unittest.main()
