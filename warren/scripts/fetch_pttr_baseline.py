#!/usr/bin/env python3
"""Fetch Warren PTTR records as a source extract for the baseline ledger."""

from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path

SERVICE = (
    "https://services1.arcgis.com/BkFxaEFNwHqX3tAw/arcgis/rest/services/"
    "FS_VCGI_OPENDATA_Cadastral_PTTR_point_WM_v1_view/FeatureServer/0/query"
)
FIELDS = [
    "OBJECTID", "span", "TownSpan", "TOWNNAME", "closeDate", "ValPdOrTrn",
    "sellEntNam", "sellFstNam", "sellLstNam", "sellerSt",
    "buyEntNam", "buyFstNam", "buyLstNam", "buyerState", "bUsePrDesc",
    "Latitude", "Longitude",
]


def fetch_all() -> list[dict]:
    features: list[dict] = []
    offset = 0
    while True:
        query = urllib.parse.urlencode(
            {
                "where": "TOWNNAME = 'Warren'",
                "outFields": ",".join(FIELDS),
                "returnGeometry": "false",
                "resultOffset": offset,
                "resultRecordCount": 1000,
                "f": "json",
            }
        )
        with urllib.request.urlopen(f"{SERVICE}?{query}", timeout=60) as response:
            page = json.loads(response.read().decode("utf-8"))
        batch = page.get("features", [])
        features.extend(batch)
        if len(batch) < 1000:
            return features
        offset += 1000


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "outputs" / "warren_pttr.json",
    )
    args = parser.parse_args()
    features = fetch_all()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"features": features}, indent=2) + "\n", encoding="utf-8")
    print(f"saved {len(features)} PTTR records to {args.output}")


if __name__ == "__main__":
    main()
