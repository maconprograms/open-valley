"""Read and promote immutable Warren baseline source runs."""

from __future__ import annotations

import json
import os
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .lineage import read_jsonl


class BaselineRepository:
    """Projection layer over the append-only source ledger.

    The current run is a manifest pointer. Promoting a run never changes its
    source records; it first creates its derived map and then atomically moves
    the pointer clients read.
    """

    def __init__(self, root: Path):
        self.root = root

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
        return read_jsonl(self.run_directory(run_id) / f"{name}.jsonl")

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
        path = self.run_directory(run_id) / "map.geojson"
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
        ownership = self._by_account("ownership_observations", run_id)
        units = self._by_account("housing_unit_claims", run_id)
        features: list[dict[str, Any]] = []
        for geometry in geometries:
            if not geometry.get("geometry"):
                continue
            account_id = geometry["account_id"]
            assessment = self._first(assessments.get(account_id, []))
            owner = self._first(ownership.get(account_id, []))
            unit_claims = units.get(account_id, [])
            mailing_state = owner.get("mailing_state") if owner else None
            features.append(
                {
                    "type": "Feature",
                    "geometry": geometry["geometry"],
                    "properties": {
                        "account_id": account_id,
                        "address": accounts.get(account_id, {}).get("address"),
                        "gis_match": geometry["link_confidence"],
                        "homestead_filed": (
                            assessment.get("homestead_filed") if assessment else None
                        ),
                        "mailing_state": mailing_state,
                        "out_of_state_mailing": bool(
                            mailing_state and mailing_state.upper() != "VT"
                        ),
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

    def map_projection(self) -> dict[str, Any]:
        path = self.run_directory() / "map.geojson"
        if not path.exists():
            raise LookupError("Current source run has not been projected")
        return json.loads(path.read_text(encoding="utf-8"))

    def summary(self) -> dict[str, Any]:
        run_id = self.current_run_id()
        accounts = self.records("property_accounts", run_id)
        assessments = self._by_account("assessment_snapshots", run_id)
        ownership = self._by_account("ownership_observations", run_id)
        units = self.records("housing_unit_claims", run_id)

        homestead = Counter()
        out_of_state = Counter()
        for account in accounts:
            account_id = account["id"]
            assessment = self._first(assessments.get(account_id, []))
            value = assessment.get("homestead_filed") if assessment else None
            homestead[{True: "yes", False: "no"}.get(value, "unknown")] += 1
            owner = self._first(ownership.get(account_id, []))
            state = owner.get("mailing_state") if owner else None
            mailing_key = "unknown" if not state else "yes" if state.upper() != "VT" else "no"
            out_of_state[mailing_key] += 1

        return {
            "source_run_id": run_id,
            "source_coverage": self.source_run(run_id).get("coverage", {}),
            "tax_accounts": {"total": len(accounts)},
            "housing_unit_claims": {
                "total": len(units),
                "by_evidence_level": dict(Counter(unit["evidence_level"] for unit in units)),
            },
            "homestead_filed": self._counts_with_total(homestead),
            "out_of_state_mailing": self._counts_with_total(out_of_state),
        }

    @staticmethod
    def _counts_with_total(counts: Counter[str]) -> dict[str, int]:
        return {
            "yes": counts["yes"],
            "no": counts["no"],
            "unknown": counts["unknown"],
            "known": counts["yes"] + counts["no"],
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
        return {
            "source_run_id": run_id,
            "account": account,
            "assessment": assessment,
            "housing_unit_claims": unit_claims,
            "ownership_observations": ownership,
            "mailing_states": sorted(
                {record["mailing_state"] for record in ownership if record.get("mailing_state")}
            ),
            "transfer_events": transfers,
        }

    def transfer_events(self) -> list[dict[str, Any]]:
        return self.records("transfer_events")

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
