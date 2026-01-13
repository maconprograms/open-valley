#!/usr/bin/env python3
"""
Test script to fetch The Bridges (42 LOWER PHASE RD) data from Vermont's API.
This will be our test case for the unified import.
"""

import httpx
import json
from collections import Counter

# Vermont ArcGIS REST API endpoint
API_URL = "https://services1.arcgis.com/BkFxaEFNwHqX3tAw/arcgis/rest/services/FS_VCGI_OPENDATA_Cadastral_VTPARCELS_poly_standardized_parcels_SP_v1/FeatureServer/0/query"

def fetch_bridges_data():
    """Fetch all parcels at 42 LOWER PHASE RD in Warren."""

    params = {
        "where": "TOWN='WARREN' AND E911ADDR='42 LOWER PHASE RD'",
        "outFields": "*",
        "returnGeometry": "false",
        "f": "json",
    }

    print("Fetching data from Vermont API...")
    print(f"Query: TOWN='WARREN' AND E911ADDR='42 LOWER PHASE RD'")
    print("-" * 60)

    response = httpx.get(API_URL, params=params, timeout=30.0)
    response.raise_for_status()
    data = response.json()

    features = data.get("features", [])
    print(f"\nTotal rows returned: {len(features)}")

    if not features:
        print("No data found!")
        return

    # Extract attributes from features
    records = [f["attributes"] for f in features]

    # Analyze the data
    print("\n" + "=" * 60)
    print("ANALYSIS")
    print("=" * 60)

    # Count unique owners
    owners = [r.get("OWNER1") for r in records if r.get("OWNER1")]
    unique_owners = set(owners)
    print(f"\nUnique owners: {len(unique_owners)}")

    # Owner frequency
    owner_counts = Counter(owners)
    print("\nOwner distribution:")
    for owner, count in owner_counts.most_common(10):
        print(f"  {owner}: {count} parcels")

    # SPANs
    spans = [r.get("SPAN") for r in records if r.get("SPAN")]
    print(f"\nUnique SPANs: {len(set(spans))}")
    print("Sample SPANs:")
    for span in sorted(set(spans))[:10]:
        print(f"  {span}")

    # Homestead analysis
    homestead_values = [r.get("HSTED_FLG") for r in records]
    homestead_counts = Counter(homestead_values)
    print(f"\nHomestead flag distribution:")
    for flag, count in homestead_counts.items():
        print(f"  {flag}: {count}")

    # Property descriptions
    descriptions = [r.get("DESCPROP") for r in records if r.get("DESCPROP")]
    desc_counts = Counter(descriptions)
    print(f"\nProperty descriptions:")
    for desc, count in desc_counts.most_common():
        print(f"  {desc}: {count}")

    # Acreage
    acreages = [r.get("ACRESGL") for r in records if r.get("ACRESGL")]
    if acreages:
        print(f"\nAcreage range: {min(acreages):.4f} - {max(acreages):.4f}")
        print(f"Total acreage: {sum(acreages):.4f}")

    # Real value (REESSION)
    real_values = [r.get("REAL_FLV") for r in records if r.get("REAL_FLV")]
    if real_values:
        print(f"\nReal value range: ${min(real_values):,.0f} - ${max(real_values):,.0f}")
        print(f"Total real value: ${sum(real_values):,.0f}")

    # Sample record - show all fields
    print("\n" + "=" * 60)
    print("SAMPLE RECORD (first parcel)")
    print("=" * 60)
    sample = records[0]
    for key, value in sorted(sample.items()):
        if value is not None:
            print(f"  {key}: {value}")

    # Look for specific SPAN
    print("\n" + "=" * 60)
    print("LOOKING FOR SPAN C-219-0014")
    print("=" * 60)
    target_span = "C-219-0014"
    matching = [r for r in records if r.get("SPAN") == target_span]
    if matching:
        print(f"Found {len(matching)} record(s) with SPAN {target_span}")
        for r in matching:
            print(f"  Owner: {r.get('OWNER1')}")
            print(f"  Description: {r.get('DESCPROP')}")
            print(f"  Homestead: {r.get('HSTED_FLG')}")
            print(f"  Real Value: ${r.get('REAL_FLV', 0):,.0f}")
    else:
        print(f"No exact match for SPAN {target_span}")
        # Try partial match
        partial = [r for r in records if target_span in str(r.get("SPAN", ""))]
        if partial:
            print(f"Partial matches: {[r.get('SPAN') for r in partial]}")

    return records


if __name__ == "__main__":
    fetch_bridges_data()
