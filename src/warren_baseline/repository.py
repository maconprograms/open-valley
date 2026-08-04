"""Read and promote immutable Warren baseline source runs."""

from __future__ import annotations

import json
import os
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .lineage import read_jsonl
from pydantic import ValidationError

from .schema import HumanReview, ReviewSubject


TAX_STATUS_BUCKETS = ("homestead_filed", "non_homestead", "unknown")
MAP_PROJECTION_FILENAME = "map-tax-status-v1.geojson"
REVIEW_SUBJECTS = tuple(subject.value for subject in ReviewSubject)


class ReviewLedgerError(ValueError):
    """A locally-authored human-review ledger could not be read safely."""


class BaselineRepository:
    """Projection layer over the append-only source ledger.

    The current run is a manifest pointer. Promoting a run never changes its
    source records; it first creates its derived map and then atomically moves
    the pointer clients read.
    """

    def __init__(self, root: Path, review_root: Path | None = None):
        self.root = root
        self.review_root = review_root or root.parent.parent / "reviews"
        self._records_cache: dict[Path, tuple[int, list[dict[str, Any]]]] = {}

    @property
    def manifest_path(self) -> Path:
        return self.root / "manifest.json"

    def manifest(self) -> dict[str, Any]:
        if not self.manifest_path.exists():
            return {"version": 1, "runs": []}
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def current_run_id(self) -> str:
        manifest = self.manifest()
        run_id = manifest.get("current_run")
        if not run_id:
            raise LookupError("No baseline source run has been promoted")
        return run_id

    def run_directory(self, run_id: str | None = None) -> Path:
        run_id = run_id or self.current_run_id()
        path = self.root / "runs" / run_id
        if not path.is_dir():
            raise LookupError(f"Baseline source run does not exist: {run_id}")
        return path

    def records(self, name: str, run_id: str | None = None) -> list[dict[str, Any]]:
        path = self.run_directory(run_id) / f"{name}.jsonl"
        modified_at = path.stat().st_mtime_ns
        cached = self._records_cache.get(path)
        if cached and cached[0] == modified_at:
            return cached[1]
        records = read_jsonl(path)
        self._records_cache[path] = (modified_at, records)
        return records

    def source_run(self, run_id: str | None = None) -> dict[str, Any]:
        path = self.run_directory(run_id) / "source_run.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def promote(self, run_id: str) -> None:
        run = self.source_run(run_id)
        if run.get("status") != "validated":
            raise ValueError(f"Only validated source runs can be promoted: {run_id}")
        self._write_map_projection(run_id)
        manifest = self.manifest()
        manifest["current_run"] = run_id
        manifest["runs"] = sorted(set(manifest.get("runs", [])) | {run_id})
        self._write_manifest(manifest)

    def _write_manifest(self, manifest: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=self.root, delete=False
        ) as temporary_file:
            json.dump(manifest, temporary_file, indent=2, sort_keys=True)
            temporary_file.write("\n")
            temporary_path = Path(temporary_file.name)
        os.replace(temporary_path, self.manifest_path)

    def _write_map_projection(self, run_id: str) -> None:
        path = self.run_directory(run_id) / MAP_PROJECTION_FILENAME
        if path.exists():
            return
        payload = self._build_map_projection(run_id)
        with path.open("x", encoding="utf-8") as output:
            json.dump(payload, output, separators=(",", ":"))
            output.write("\n")

    def _build_map_projection(self, run_id: str) -> dict[str, Any]:
        accounts = {record["id"]: record for record in self.records("property_accounts", run_id)}
        geometries = self.records("parcel_geometries", run_id)
        assessments = self._by_account("assessment_snapshots", run_id)
        units = self._by_account("housing_unit_claims", run_id)
        features: list[dict[str, Any]] = []
        for geometry in geometries:
            if not geometry.get("geometry"):
                continue
            account_id = geometry["account_id"]
            assessment = self._first(assessments.get(account_id, []))
            unit_claims = units.get(account_id, [])
            features.append(
                {
                    "type": "Feature",
                    "geometry": geometry["geometry"],
                    "properties": {
                        "account_id": account_id,
                        "address": accounts.get(account_id, {}).get("address"),
                        "gis_match": geometry["link_confidence"],
                        "tax_status_bucket": self.tax_status_bucket(assessment),
                        "housing_unit_claims": len(unit_claims),
                        "unit_evidence_levels": sorted(
                            {claim["evidence_level"] for claim in unit_claims}
                        ),
                    },
                }
            )
        return {
            "type": "FeatureCollection",
            "source_run_id": run_id,
            "features": features,
        }

    def _by_account(self, name: str, run_id: str) -> dict[str, list[dict[str, Any]]]:
        records: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in self.records(name, run_id):
            records[record["account_id"]].append(record)
        return records

    @staticmethod
    def _first(records: list[dict[str, Any]]) -> dict[str, Any] | None:
        return records[0] if records else None

    @staticmethod
    def tax_status_bucket(assessment: dict[str, Any] | None) -> str:
        """Return a map-safe bucket from the direct HSDECL observation only."""
        homestead_filed = assessment.get("homestead_filed") if assessment else None
        if homestead_filed is True:
            return "homestead_filed"
        if homestead_filed is False:
            return "non_homestead"
        return "unknown"

    def map_projection_path(self) -> Path:
        run_id = self.current_run_id()
        path = self.run_directory(run_id) / MAP_PROJECTION_FILENAME
        if not path.exists():
            raise LookupError(
                f"Baseline source run has no materialized map projection: {run_id}"
            )
        return path

    def map_projection(self) -> dict[str, Any]:
        path = self.map_projection_path()
        return json.loads(path.read_text(encoding="utf-8"))

    def summary(self) -> dict[str, Any]:
        run_id = self.current_run_id()
        accounts = self.records("property_accounts", run_id)
        assessments = self._by_account("assessment_snapshots", run_id)
        units = self.records("housing_unit_claims", run_id)

        tax_status = Counter()
        for account in accounts:
            account_id = account["id"]
            assessment = self._first(assessments.get(account_id, []))
            tax_status[self.tax_status_bucket(assessment)] += 1

        return {
            "source_run_id": run_id,
            "source_coverage": self.source_run(run_id).get("coverage", {}),
            "tax_accounts": {"total": len(accounts)},
            "housing_unit_claims": {
                "total": len(units),
                "by_evidence_level": dict(Counter(unit["evidence_level"] for unit in units)),
            },
            "tax_status_buckets": {
                bucket: tax_status[bucket]
                for bucket in TAX_STATUS_BUCKETS
            },
        }

    def account_detail(self, account_id: str) -> dict[str, Any]:
        run_id = self.current_run_id()
        accounts = {record["id"]: record for record in self.records("property_accounts", run_id)}
        account = accounts.get(account_id)
        if not account:
            raise LookupError(f"Unknown tax account: {account_id}")
        ownership = self._by_account("ownership_observations", run_id).get(account_id, [])
        assessment = self._first(
            self._by_account("assessment_snapshots", run_id).get(account_id, [])
        )
        unit_claims = self._by_account("housing_unit_claims", run_id).get(account_id, [])
        transfers = [
            event
            for event in self.records("transfer_events", run_id)
            if event.get("account_id") == account_id
        ]
        reviews = self.human_reviews(account_id, source_run_id=run_id)
        review_status_by_subject = {subject: "unreviewed" for subject in REVIEW_SUBJECTS}
        for review in reviews:
            review_status_by_subject[review["subject"]] = review["status"]
        return {
            "source_run_id": run_id,
            "account": account,
            "assessment": assessment,
            "housing_unit_claims": unit_claims,
            "ownership_observations": ownership,
            "review_status_by_subject": review_status_by_subject,
            "human_reviews": reviews,
            "transfer_events": transfers,
        }

    @property
    def review_path(self) -> Path:
        return self.review_root / "property_reviews.jsonl"

    def human_reviews(
        self, account_id: str | None = None, source_run_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Read validated local reviews without mutating the raw source ledger."""
        if not self.review_path.exists():
            return []
        try:
            records = read_jsonl(self.review_path)
            reviews = [
                HumanReview.model_validate(record).model_dump(mode="json")
                for record in records
            ]
        except (json.JSONDecodeError, OSError, ValidationError) as error:
            raise ReviewLedgerError(f"Invalid human-review ledger: {error}") from error
        if account_id:
            reviews = [review for review in reviews if review["account_id"] == account_id]
        if source_run_id:
            reviews = [review for review in reviews if review["source_run_id"] == source_run_id]
        return sorted(reviews, key=lambda review: review["reviewed_at"])

    def review_queue(self) -> list[dict[str, Any]]:
        """Minimal private-review queue; raw mailing fields remain out of the map."""
        run_id = self.current_run_id()
        assessments = self._by_account("assessment_snapshots", run_id)
        review_status_by_account = {
            account["id"]: {subject: "unreviewed" for subject in REVIEW_SUBJECTS}
            for account in self.records("property_accounts", run_id)
        }
        for review in self.human_reviews(source_run_id=run_id):
            review_status_by_account.setdefault(
                review["account_id"], {subject: "unreviewed" for subject in REVIEW_SUBJECTS}
            )[review["subject"]] = review["status"]
        return [
            {
                "account_id": account["id"],
                "address": account.get("address"),
                "tax_status_bucket": self.tax_status_bucket(
                    self._first(assessments.get(account["id"], []))
                ),
                "review_status_by_subject": review_status_by_account[account["id"]],
            }
            for account in self.records("property_accounts", run_id)
        ]

    def transfer_events(self) -> list[dict[str, Any]]:
        return self.records("transfer_events")

    def homestead_trend(self) -> dict[str, Any]:
        """Return direct annual Grand List filing observations, with coverage intact."""
        path = self.root.parent / "historical" / "warren_homestead_accounts_by_year.json"
        if not path.exists():
            raise LookupError("No historical Warren homestead extraction is available")
        return {
            "measure": "homestead filed among Grand List records with PARCID",
            "unit": "grand_list_records",
            "caveat": (
                "This is an annual HSDECL filing rate, not a housing-unit rate or a "
                "direct measure of full-time residency. Source coverage can change by year."
            ),
            "observations": json.loads(path.read_text(encoding="utf-8")),
        }

    def sources(self) -> dict[str, Any]:
        run_id = self.current_run_id()
        source_records = self.records("source_records", run_id)
        references: dict[str, dict[str, Any]] = {}
        for record in source_records:
            source = record["source"]
            references.setdefault(source["source_key"].split(":", 1)[0], source)
        for event in self.records("transfer_events", run_id):
            source = event["source"]
            references.setdefault(source["source_key"].split(":", 1)[0], source)
        return {"source_run": self.source_run(run_id), "sources": list(references.values())}
