import csv
import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from src.warren_baseline.lineage import read_jsonl
from warren.scripts.build_baseline import materialize_baseline

FIXTURES = Path(__file__).parent / "fixtures"


class BuildBaselineTests(unittest.TestCase):
    def write_geojson(self, directory: Path) -> Path:
        path = directory / "parcels.geojson"
        path.write_text(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "properties": {
                                "PARCID": "001000-1",
                                "SPAN": "690-219-10513",
                                "OWNER1": "CARTER PATRICIA SUE",
                                "HSDECL": "N",
                                "GLYEAR": "2025",
                                "STGL": "MA",
                                "CITYGL": "Cambridge",
                                "ZIPGL": "02139",
                                "DESCPROP": "1.0 ACRES & 2 DWLS",
                                "REAL_FLV": "500000",
                                "LAND_LV": "100000",
                                "IMPRV_LV": "400000",
                            },
                            "geometry": {
                                "type": "Polygon",
                                "coordinates": [
                                    [
                                        [-72.8, 44.1],
                                        [-72.8, 44.2],
                                        [-72.7, 44.2],
                                        [-72.8, 44.1],
                                    ]
                                ],
                            },
                        }
                    ],
                }
            )
        )
        return path

    def write_joined(self, directory: Path) -> Path:
        path = directory / "joined.csv"
        with path.open("w", newline="") as output:
            writer = csv.DictWriter(
                output,
                fieldnames=[
                    "parcel_id",
                    "owner",
                    "owner_mailing",
                    "SPAN",
                    "location",
                    "gis_match",
                    "gis_PARCID",
                    "gis_lon",
                    "gis_lat",
                    "gis_DESCPROP",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "parcel_id": "0010001",
                    "owner": "CARTER PATRICIA SUE",
                    "owner_mailing": "CARTER PATRICIA SUE | PO BOX 1 | CAMBRIDGE, MA 02139",
                    "SPAN": "690-219-10513",
                    "location": "15 BROOK RD",
                    "gis_match": "parcid",
                    "gis_PARCID": "001000-1",
                    "gis_lon": "-72.8",
                    "gis_lat": "44.1",
                    "gis_DESCPROP": "1.0 ACRES & 2 DWLS",
                }
            )
        return path

    def test_materializer_preserves_facts_and_uses_run_scoped_artifacts(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            result = materialize_baseline(
                joined_path=self.write_joined(root),
                parcels_path=self.write_geojson(root),
                output_root=root / "baseline",
                retrieved_at=datetime(2026, 8, 3, tzinfo=UTC),
            )

            run_dir = root / "baseline" / "runs" / result.run_id
            accounts = read_jsonl(run_dir / "property_accounts.jsonl")
            units = read_jsonl(run_dir / "housing_unit_claims.jsonl")
            assessments = read_jsonl(run_dir / "assessment_snapshots.jsonl")
            ownership = read_jsonl(run_dir / "ownership_observations.jsonl")

            self.assertEqual(len(accounts), 1)
            self.assertEqual(len(units), 2)
            self.assertTrue(all(unit["evidence_level"] == "documented" for unit in units))
            self.assertFalse(assessments[0]["homestead_filed"])
            self.assertEqual(ownership[0]["mailing_state"], "MA")
            self.assertEqual(result.coverage["accounts"], 1)
            manifest = json.loads((root / "baseline" / "manifest.json").read_text())
            self.assertEqual(manifest["last_staged_run"], result.run_id)

    def test_repeated_input_reuses_immutable_run(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            kwargs = {
                "joined_path": self.write_joined(root),
                "parcels_path": self.write_geojson(root),
                "output_root": root / "baseline",
                "retrieved_at": datetime(2026, 8, 3, tzinfo=UTC),
            }

            first = materialize_baseline(**kwargs)
            artifact = root / "baseline" / "runs" / first.run_id / "property_accounts.jsonl"
            before = artifact.read_bytes()
            second = materialize_baseline(**kwargs)

            self.assertEqual(first.run_id, second.run_id)
            self.assertEqual(before, artifact.read_bytes())


if __name__ == "__main__":
    unittest.main()
