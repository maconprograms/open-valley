#!/usr/bin/env python3
"""Materialize an immutable, evidence-first Warren baseline source run.

This script intentionally uses the standalone Warren extracts instead of the
legacy database models. It records what the sources say, including coverage and
uncertainty, without inferring residence, second-home status, or transitions.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from src.warren_baseline.lineage import (
    canonical_account_id,
    checksum,
    normalized_owner_key,
    source_record_id,
    utc_now,
    write_jsonl,
)
from src.warren_baseline.schema import (
    AssessmentSnapshot,
    HousingUnitClaim,
    LinkConfidence,
    NormalizedPartyMatch,
    OwnershipObservation,
    ParcelGeometry,
    PartyMatchConfidence,
    PartyMatchReviewState,
    PropertyAccount,
    SourceRecord,
    SourceReference,
    SourceRun,
    TransferEvent,
    UnitEvidenceLevel,
)

ROOT = Path(__file__).resolve().parents[2]
OUTPUTS = ROOT / "warren" / "outputs"
BASELINE_OUTPUTS = OUTPUTS / "baseline"
NEMRC_SOURCE = "https://nemrc.info/web_data/vtwarr/camadetailT.php?prop={parcel_id}"
VCGI_SOURCE = (
    "https://services1.arcgis.com/BkFxaEFNwHqX3tAw/arcgis/rest/services/"
    "FS_VCGI_OPENDATA_Cadastral_VTPARCELS_poly_standardized_parcels_SP_v1/FeatureServer/0"
)


@dataclass(frozen=True)
class MaterializationResult:
    run_id: str
    coverage: dict[str, int]
    reused: bool = False


def clean_identifier(value: str | None) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", value or "").upper()


def parse_int(value: str | int | float | None) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except ValueError:
        return None


def parse_date_from_epoch(value: Any) -> date | None:
    if value in (None, ""):
        return None
    try:
        return datetime.fromtimestamp(int(value) / 1000).date()
    except (TypeError, ValueError, OSError):
        return None


def parse_unit_count(descprop: str | None) -> tuple[int, UnitEvidenceLevel, str]:
    """Return source-supported unit claims, never an occupancy classification."""
    text = (descprop or "").upper()
    explicit = re.search(r"&\s*(\d+)\s*DWLS?", text)
    if explicit:
        return (
            int(explicit.group(1)),
            UnitEvidenceLevel.DOCUMENTED,
            "DESCPROP explicit dwelling count",
        )
    if re.search(r"&\s*DWL(?:[.\s:]|$)", text):
        return 1, UnitEvidenceLevel.DOCUMENTED, "DESCPROP dwelling signal"
    if "& CONDO" in text:
        return 1, UnitEvidenceLevel.DOCUMENTED, "DESCPROP condominium signal"
    if "& MF" in text:
        return 1, UnitEvidenceLevel.INFERRED, "DESCPROP multi-family signal without count"
    return 0, UnitEvidenceLevel.UNKNOWN, "No explicit dwelling signal"


def parse_mailing_block(value: str | None) -> dict[str, str | None]:
    """Use a NEMRC mailing block only as a fallback to VCGI mailing fields."""
    if not value:
        return {"address": None, "city": None, "state": None, "zip": None}
    pieces = [piece.strip() for piece in value.split("|") if piece.strip()]
    tail = pieces[-1] if pieces else ""
    match = re.search(r"^(.*?),\s*([A-Z]{2})\s*(\d{5}(?:-\d{4})?)?$", tail.upper())
    if match:
        return {
            "address": " | ".join(pieces[1:-1]) or None,
            "city": match.group(1).title() or None,
            "state": match.group(2),
            "zip": match.group(3),
        }
    return {"address": " | ".join(pieces[1:]) or None, "city": None, "state": None, "zip": None}


def source_ref(
    run_id: str,
    key: str,
    fields: list[str],
    retrieved_at: datetime,
    source_url: str | None = None,
    source_extract: str | None = None,
    source_effective_date: date | None = None,
) -> SourceReference:
    return SourceReference(
        source_run_id=run_id,
        source_key=key,
        source_url=source_url,
        source_extract=source_extract,
        source_fields=fields,
        retrieved_at=retrieved_at,
        source_effective_date=source_effective_date,
    )


def load_parcels(path: Path) -> tuple[dict[str, dict], dict[str, dict]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    by_parcid: dict[str, dict] = {}
    by_span: dict[str, dict] = {}
    for feature in payload.get("features", []):
        props = feature.get("properties") or {}
        parcid = clean_identifier(props.get("PARCID"))
        span = clean_identifier(props.get("SPAN"))
        if parcid:
            by_parcid.setdefault(parcid, feature)
        if span:
            by_span.setdefault(span, feature)
    return by_parcid, by_span


def stable_run_id(
    joined_path: Path, parcels_path: Path, pttr_path: Path | None
) -> tuple[str, dict[str, str]]:
    inputs = {"joined": checksum(joined_path), "parcels": checksum(parcels_path)}
    if pttr_path and pttr_path.exists():
        inputs["pttr"] = checksum(pttr_path)
    digest = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()[:16]
    return f"warren-{digest}", inputs


def write_json(path: Path, payload: dict) -> None:
    with path.open("x", encoding="utf-8") as output:
        json.dump(payload, output, indent=2, sort_keys=True, default=str)
        output.write("\n")


def materialize_baseline(
    *,
    joined_path: Path,
    parcels_path: Path,
    output_root: Path = BASELINE_OUTPUTS,
    pttr_path: Path | None = None,
    retrieved_at: datetime | None = None,
) -> MaterializationResult:
    """Stage one reproducible run from source extracts without mutating older runs."""
    retrieved_at = retrieved_at or utc_now()
    run_id, checksums = stable_run_id(joined_path, parcels_path, pttr_path)
    run_dir = output_root / "runs" / run_id
    if run_dir.exists():
        run = json.loads((run_dir / "source_run.json").read_text(encoding="utf-8"))
        return MaterializationResult(run_id=run_id, coverage=run.get("coverage", {}), reused=True)

    by_parcid, by_span = load_parcels(parcels_path)
    with joined_path.open(newline="", encoding="utf-8-sig") as source_file:
        joined_rows = list(csv.DictReader(source_file))

    source_records: list[SourceRecord] = []
    accounts: list[PropertyAccount] = []
    geometries: list[ParcelGeometry] = []
    units: list[HousingUnitClaim] = []
    assessments: list[AssessmentSnapshot] = []
    ownership: list[OwnershipObservation] = []
    matches: list[NormalizedPartyMatch] = []
    account_by_span: dict[str, list[str]] = {}
    matched_geometry = 0

    for row in joined_rows:
        parcel_id = (row.get("parcel_id") or "").strip()
        if not parcel_id:
            continue
        account_id = canonical_account_id("Warren", parcel_id)
        parcid = row.get("gis_PARCID") or None
        span = row.get("SPAN") or None
        match_method = (row.get("gis_match") or "none").lower()
        feature = by_parcid.get(clean_identifier(parcid))
        if feature is None and span:
            feature = by_span.get(clean_identifier(span))
        props = feature.get("properties", {}) if feature else {}
        confidence = LinkConfidence.EXACT_PARCID if match_method == "parcid" else (
            LinkConfidence.EXACT_SPAN if match_method == "span" else LinkConfidence.UNMATCHED
        )
        if feature:
            matched_geometry += 1

        nemrc_ref = source_ref(
            run_id,
            f"nemrc:{parcel_id}",
            ["parcel_id", "owner", "owner_mailing", "SPAN", "location"],
            retrieved_at,
            source_url=NEMRC_SOURCE.format(parcel_id=parcel_id),
            source_extract=joined_path.name,
        )
        vcgi_ref = source_ref(
            run_id,
            f"vcgi:{props.get('OBJECTID') or parcid or parcel_id}",
            ["PARCID", "SPAN", "OWNER1", "OWNER2", "HSDECL", "GLYEAR", "STGL", "DESCPROP"],
            retrieved_at,
            source_url=VCGI_SOURCE,
            source_extract=parcels_path.name,
            source_effective_date=date(int(props["GLYEAR"]), 1, 1)
            if str(props.get("GLYEAR") or "").isdigit()
            else None,
        )
        source_records.extend(
            [
                SourceRecord(
                    id=source_record_id(run_id, nemrc_ref.source_key),
                    source=nemrc_ref,
                    raw_values=row,
                ),
                SourceRecord(
                    id=source_record_id(run_id, vcgi_ref.source_key),
                    source=vcgi_ref,
                    raw_values=props,
                ),
            ]
        )
        accounts.append(
            PropertyAccount(
                id=account_id,
                town="Warren",
                nemrc_parcel_id=parcel_id,
                parcid=parcid,
                span=span,
                address=row.get("location") or props.get("E911ADDR"),
                gis_match=confidence,
                source=nemrc_ref,
            )
        )
        if span:
            account_by_span.setdefault(clean_identifier(span), []).append(account_id)

        geometries.append(
            ParcelGeometry(
                id=f"geometry:{account_id}",
                account_id=account_id,
                geometry=feature.get("geometry") if feature else None,
                centroid_lon=float(row["gis_lon"]) if row.get("gis_lon") else None,
                centroid_lat=float(row["gis_lat"]) if row.get("gis_lat") else None,
                link_confidence=confidence,
                source=vcgi_ref,
            )
        )

        descprop = props.get("DESCPROP") or row.get("gis_DESCPROP")
        count, level, reason = parse_unit_count(descprop)
        if not count and parse_int(props.get("HSITEVAL") or row.get("Housesite")):
            count, level, reason = 1, UnitEvidenceLevel.INFERRED, "Housesite value signal"
        if not count:
            count = 1
        for index in range(1, count + 1):
            units.append(
                HousingUnitClaim(
                    id=f"unit:{account_id}:{index}",
                    account_id=account_id,
                    evidence_level=level,
                    evidence_reason=reason,
                    source=vcgi_ref,
                    excluded_reason=None,
                )
            )

        hsdecl = props.get("HSDECL")
        assessments.append(
            AssessmentSnapshot(
                id=f"assessment:{account_id}:{props.get('GLYEAR') or 'unknown'}",
                account_id=account_id,
                grand_list_year=parse_int(props.get("GLYEAR")),
                homestead_filed=True if hsdecl == "Y" else False if hsdecl == "N" else None,
                property_category=props.get("CAT"),
                assessed_total=parse_int(props.get("REAL_FLV") or row.get("Total")),
                assessed_land=parse_int(props.get("LAND_LV") or row.get("Land Value")),
                assessed_improvement=parse_int(props.get("IMPRV_LV") or row.get("Dwelling Value")),
                source=vcgi_ref,
            )
        )

        mailing = parse_mailing_block(row.get("owner_mailing"))
        mailing = {
            "address": props.get("ADDRGL1") or props.get("ADDRGL2") or mailing["address"],
            "city": props.get("CITYGL") or mailing["city"],
            "state": props.get("STGL") or mailing["state"],
            "zip": props.get("ZIPGL") or mailing["zip"],
        }
        owner_values = [row.get("owner"), props.get("OWNER1"), props.get("OWNER2")]
        seen_owner_text: set[str] = set()
        for position, owner_text in enumerate(owner_values, start=1):
            owner_text = (owner_text or "").strip()
            if not owner_text or owner_text in seen_owner_text:
                continue
            seen_owner_text.add(owner_text)
            observation = OwnershipObservation(
                id=f"ownership:{account_id}:{position}",
                account_id=account_id,
                owner_text=owner_text,
                owner_position=position,
                mailing_address=mailing["address"],
                mailing_city=mailing["city"],
                mailing_state=mailing["state"],
                mailing_zip=mailing["zip"],
                source=nemrc_ref if position == 1 else vcgi_ref,
            )
            ownership.append(observation)
            matches.append(
                NormalizedPartyMatch(
                    id=f"match:{observation.id}",
                    ownership_observation_id=observation.id,
                    normalized_party_key=normalized_owner_key(owner_text),
                    confidence=PartyMatchConfidence.EXACT,
                    review_state=PartyMatchReviewState.UNREVIEWED,
                    source_owner_text=owner_text,
                )
            )

    transfers = load_transfer_events(pttr_path, run_id, retrieved_at, account_by_span)
    coverage = {
        "accounts": len(accounts),
        "parcel_geometries": len(geometries),
        "matched_geometries": matched_geometry,
        "unmatched_accounts": len(accounts) - matched_geometry,
        "housing_unit_claims": len(units),
        "transfer_events": len(transfers),
    }
    run = SourceRun(
        id=run_id,
        town="Warren",
        retrieved_at=retrieved_at,
        status="validated",
        input_checksums=checksums,
        coverage=coverage,
        completed_at=utc_now(),
    )

    run_dir.mkdir(parents=True, exist_ok=False)
    write_json(run_dir / "source_run.json", run.model_dump(mode="json"))
    write_jsonl(run_dir / "source_records.jsonl", source_records)
    write_jsonl(run_dir / "property_accounts.jsonl", accounts)
    write_jsonl(run_dir / "parcel_geometries.jsonl", geometries)
    write_jsonl(run_dir / "housing_unit_claims.jsonl", units)
    write_jsonl(run_dir / "assessment_snapshots.jsonl", assessments)
    write_jsonl(run_dir / "ownership_observations.jsonl", ownership)
    write_jsonl(run_dir / "normalized_party_matches.jsonl", matches)
    write_jsonl(run_dir / "transfer_events.jsonl", transfers)

    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / "manifest.json"
    manifest = (
        json.loads(manifest_path.read_text())
        if manifest_path.exists()
        else {"version": 1, "runs": []}
    )
    manifest["last_staged_run"] = run_id
    manifest["runs"] = sorted(set(manifest.get("runs", [])) | {run_id})
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return MaterializationResult(run_id=run_id, coverage=coverage)


def import_materialized_run(
    output_root: Path,
    run_id: str,
    ledger: Any,
) -> Any:
    """Send a run from an operator-controlled workspace to private Postgres.

    The caller supplies the protected ledger connection. This helper does not
    read environment variables or print source values, paths, or credentials.
    """
    from src.warren_baseline.private_ledger import load_private_run_directory

    source_run, records = load_private_run_directory(output_root / "runs" / run_id)
    return ledger.import_run(source_run, records)


def load_transfer_events(
    pttr_path: Path | None,
    run_id: str,
    retrieved_at: datetime,
    account_by_span: dict[str, list[str]],
) -> list[TransferEvent]:
    if not pttr_path or not pttr_path.exists():
        return []
    payload = json.loads(pttr_path.read_text(encoding="utf-8"))
    events: list[TransferEvent] = []
    for feature in payload.get("features", []):
        attrs = feature.get("attributes") or {}
        object_id = str(attrs.get("OBJECTID") or "")
        if not object_id:
            continue
        span = attrs.get("span") or attrs.get("TownSpan")
        linked_accounts = account_by_span.get(clean_identifier(span), [])
        account_id = linked_accounts[0] if len(linked_accounts) == 1 else None
        confidence = LinkConfidence.EXACT_SPAN if linked_accounts else LinkConfidence.UNMATCHED
        source = source_ref(
            run_id,
            f"pttr:{object_id}",
            ["OBJECTID", "span", "closeDate", "ValPdOrTrn", "sellerSt", "buyerState", "bUsePrDesc"],
            retrieved_at,
            source_url="https://services1.arcgis.com/BkFxaEFNwHqX3tAw/arcgis/rest/services/FS_VCGI_OPENDATA_Cadastral_PTTR_point_WM_v1_view/FeatureServer/0",
            source_extract=pttr_path.name,
        )
        seller_person = " ".join(
            filter(None, [attrs.get("sellFstNam"), attrs.get("sellLstNam")])
        )
        buyer_person = " ".join(
            filter(None, [attrs.get("buyFstNam"), attrs.get("buyLstNam")])
        )
        events.append(
            TransferEvent(
                id=f"transfer:{object_id}",
                account_id=account_id,
                source_object_id=object_id,
                transfer_date=parse_date_from_epoch(attrs.get("closeDate")),
                sale_price=parse_int(attrs.get("ValPdOrTrn")),
                span=span,
                seller_name=" / ".join(
                    part
                    for part in [attrs.get("sellEntNam"), seller_person]
                    if part
                )
                or None,
                seller_state=attrs.get("sellerSt"),
                buyer_name=" / ".join(
                    part
                    for part in [attrs.get("buyEntNam"), buyer_person]
                    if part
                )
                or None,
                buyer_state=attrs.get("buyerState"),
                buyer_stated_use=attrs.get("bUsePrDesc"),
                latitude=attrs.get("Latitude"),
                longitude=attrs.get("Longitude"),
                link_confidence=confidence,
                source=source,
            )
        )
    return events


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--joined", type=Path, default=OUTPUTS / "warren_joined.csv")
    parser.add_argument("--parcels", type=Path, default=OUTPUTS / "warren_parcels.geojson")
    parser.add_argument("--pttr", type=Path)
    parser.add_argument("--output", type=Path, default=BASELINE_OUTPUTS)
    parser.add_argument(
        "--import-private-ledger",
        action="store_true",
        help="operator-only: append the materialized run to protected Postgres",
    )
    args = parser.parse_args()
    result = materialize_baseline(
        joined_path=args.joined,
        parcels_path=args.parcels,
        output_root=args.output,
        pttr_path=args.pttr,
    )
    if args.import_private_ledger:
        from src.warren_baseline.private_ledger import (
            PrivateLedger,
            PrivateLedgerError,
            connect_private_ledger,
            private_database_url,
        )

        try:
            ledger = PrivateLedger(connect_private_ledger(private_database_url()))
            import_materialized_run(args.output, result.run_id, ledger)
        except PrivateLedgerError as error:
            raise SystemExit(str(error)) from error
    action = "reused" if result.reused else "staged"
    print(f"{action} {result.run_id}: {result.coverage}")


if __name__ == "__main__":
    main()
