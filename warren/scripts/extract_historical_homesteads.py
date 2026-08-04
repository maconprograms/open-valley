#!/usr/bin/env python3
"""Download and summarize annual Warren HSDECL snapshots from VCGI archives.

Archives are raw, re-fetchable source inputs in ``warren/raw_vcgi_snapshots/``.
This script writes a compact, committed Warren-only annual extract and summary.
It intentionally reports Grand List record/account rates, not housing-unit rates.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import tempfile
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

import pyogrio.raw

ARCHIVE_ROOT = (
    "https://archives.vcgi.vermont.gov/files/"
    "Historical%20Snapshots%20of%20Vermont%20Parcel%20GIS%20Data"
)
LAYER = "Cadastral_VTPARCELS_poly_standardized_parcels"
FIELDS = ["PARCID", "SPAN", "GLYEAR", "TOWN", "HSDECL", "OWNER1", "STGL", "DESCPROP", "CAT"]
SNAPSHOTS = {
    2017: "20190218",
    2018: "20200203",
    2019: "20210118",
    2020: "20211025",
    2021: "20221010",
    2022: "20231016",
    2023: "20241028",
    2024: "20250915",
}
CURRENT_VCGI_SOURCE = (
    "https://services1.arcgis.com/BkFxaEFNwHqX3tAw/arcgis/rest/services/"
    "FS_VCGI_OPENDATA_Cadastral_VTPARCELS_poly_standardized_parcels_SP_v1/FeatureServer/0"
)


def archive_url(snapshot_date: str) -> str:
    return f"{ARCHIVE_ROOT}/SNAPSHOT_VTPARCELS_{snapshot_date}.zip"


def download_archive(snapshot_date: str, raw_directory: Path) -> Path:
    raw_directory.mkdir(parents=True, exist_ok=True)
    archive = raw_directory / f"SNAPSHOT_VTPARCELS_{snapshot_date}.zip"
    if archive.exists() and archive.stat().st_size:
        return archive
    temporary = archive.with_suffix(".part")
    with urllib.request.urlopen(archive_url(snapshot_date), timeout=120) as response:
        with temporary.open("wb") as output:
            shutil.copyfileobj(response, output)
    temporary.replace(archive)
    return archive


def rows_from_archive(archive: Path) -> list[dict[str, Any]]:
    with tempfile.TemporaryDirectory(prefix="vcgi-snapshot-") as temporary_directory:
        temporary = Path(temporary_directory)
        with zipfile.ZipFile(archive) as source:
            source.extractall(temporary)
        geodatabase = next(temporary.rglob("*.gdb"))
        metadata, _, _, arrays = pyogrio.raw.read(
            geodatabase,
            layer=LAYER,
            where="TOWN = 'WARREN'",
            columns=FIELDS,
            read_geometry=False,
        )
        columns = dict(zip(metadata["fields"], arrays, strict=True))
        return [
            {field: normalize(value) for field, value in zip(columns, values, strict=True)}
            for values in zip(*columns.values(), strict=True)
        ]


def normalize(value: Any) -> Any:
    if value is None:
        return None
    try:
        if value != value:  # numpy's NaN without taking a numpy dependency here
            return None
    except TypeError:
        pass
    return value.item() if hasattr(value, "item") else value


def summarize(
    year: int, snapshot_date: str, rows: list[dict[str, Any]], source_url: str
) -> dict[str, Any]:
    account_rows = [row for row in rows if row.get("PARCID")]
    if not account_rows:
        return {
            "grand_list_year": year,
            "snapshot_date": snapshot_date,
            "source_url": source_url,
            "source_available_for_warren": False,
            "warren_layer_rows": len(rows),
            "grand_list_records_with_parcid": 0,
            "homestead_filed": None,
            "homestead_not_filed": None,
            "homestead_unknown": None,
            "known_homestead_denominator": None,
            "homestead_filed_percent_of_known": None,
        }
    statuses = Counter(str(row.get("HSDECL") or "").strip().upper() for row in account_rows)
    yes = statuses["Y"]
    no = statuses["N"]
    known = yes + no
    return {
        "grand_list_year": year,
        "snapshot_date": snapshot_date,
        "source_url": source_url,
        "source_available_for_warren": True,
        "warren_layer_rows": len(rows),
        "grand_list_records_with_parcid": len(account_rows),
        "homestead_filed": yes,
        "homestead_not_filed": no,
        "homestead_unknown": len(account_rows) - known,
        "known_homestead_denominator": known,
        "homestead_filed_percent_of_known": round(100 * yes / known, 2) if known else None,
    }


def rows_from_current_geojson(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        {field: normalize((feature.get("properties") or {}).get(field)) for field in FIELDS}
        for feature in payload.get("features", [])
        if (feature.get("properties") or {}).get("TOWN") == "WARREN"
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-directory", type=Path, default=Path("warren/raw_vcgi_snapshots"))
    parser.add_argument(
        "--output-directory", type=Path, default=Path("warren/outputs/historical")
    )
    parser.add_argument("--years", nargs="*", type=int, default=sorted(SNAPSHOTS))
    parser.add_argument(
        "--current-geojson", type=Path, default=Path("warren/outputs/warren_parcels.geojson")
    )
    parser.add_argument("--skip-download", action="store_true")
    args = parser.parse_args()

    summaries: list[dict[str, Any]] = []
    all_rows: list[dict[str, Any]] = []
    for year in args.years:
        snapshot_date = SNAPSHOTS[year]
        archive = args.raw_directory / f"SNAPSHOT_VTPARCELS_{snapshot_date}.zip"
        if not args.skip_download:
            archive = download_archive(snapshot_date, args.raw_directory)
        if not archive.exists():
            raise FileNotFoundError(f"Missing archive for {year}: {archive}")
        rows = rows_from_archive(archive)
        summaries.append(summarize(year, snapshot_date, rows, archive_url(snapshot_date)))
        for row in rows:
            all_rows.append({"grand_list_year": year, "snapshot_date": snapshot_date, **row})

    current_rows = rows_from_current_geojson(args.current_geojson)
    current_years = {
        int(row["GLYEAR"])
        for row in current_rows
        if str(row.get("GLYEAR") or "").isdigit()
    }
    if len(current_years) != 1:
        raise ValueError(f"Expected one current Grand List year, found: {sorted(current_years)}")
    current_year = current_years.pop()
    summaries.append(summarize(current_year, "current", current_rows, CURRENT_VCGI_SOURCE))
    for row in current_rows:
        all_rows.append({"grand_list_year": current_year, "snapshot_date": "current", **row})

    summaries.sort(key=lambda summary: summary["grand_list_year"])

    args.output_directory.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_directory / "warren_homestead_accounts_by_year.json"
    summary_path.write_text(json.dumps(summaries, indent=2, default=str) + "\n", encoding="utf-8")
    rows_path = args.output_directory / "warren_grand_list_homestead_records.csv"
    fieldnames = ["grand_list_year", "snapshot_date", *FIELDS]
    with rows_path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(all_rows)
    for summary in summaries:
        print(
            f"{summary['grand_list_year']}: {summary['homestead_filed']} / "
            f"{summary['known_homestead_denominator']} "
            f"({summary['homestead_filed_percent_of_known']}%)"
        )


if __name__ == "__main__":
    main()
