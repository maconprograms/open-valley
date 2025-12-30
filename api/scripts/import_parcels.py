"""Import Warren parcels from Vermont Geodata ArcGIS API."""

import json
import sys
from pathlib import Path

import httpx

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import SessionLocal, init_db
from src.models import Owner, Parcel, TaxStatus

# Vermont Geodata ArcGIS REST API - Standardized Parcels with Grand List data
ARCGIS_BASE = "https://services1.arcgis.com/BkFxaEFNwHqX3tAw/arcgis/rest/services"
PARCELS_LAYER = "FS_VCGI_OPENDATA_Cadastral_VTPARCELS_poly_standardized_parcels_SP_v1/FeatureServer/0"
PARCELS_URL = f"{ARCGIS_BASE}/{PARCELS_LAYER}/query"


def fetch_warren_parcels(offset: int = 0, limit: int = 1000) -> dict:
    """Fetch parcels from ArcGIS API for Warren, VT."""
    params = {
        "where": "TOWN = 'WARREN'",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",  # WGS84 for lat/lng
        "f": "geojson",
        "resultOffset": offset,
        "resultRecordCount": limit,
    }

    print(f"Fetching parcels from offset {offset}...")
    response = httpx.get(PARCELS_URL, params=params, timeout=60.0)
    response.raise_for_status()
    return response.json()


def fetch_single_parcel(address_fragment: str = "488 WOODS") -> dict:
    """Fetch a single parcel by address for testing."""
    params = {
        "where": f"TOWN = 'WARREN' AND E911ADDR LIKE '%{address_fragment}%'",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
    }

    print(f"Searching for parcel with address containing '{address_fragment}'...")
    response = httpx.get(PARCELS_URL, params=params, timeout=30.0)
    response.raise_for_status()
    return response.json()


def parse_parcel(feature: dict) -> dict:
    """Parse a GeoJSON feature into parcel data."""
    props = feature.get("properties", {})
    geom = feature.get("geometry")

    # Calculate centroid from geometry if available
    lat, lng = None, None
    if geom and geom.get("coordinates"):
        coords = geom["coordinates"]
        # For multipolygon, get first polygon's first ring
        if geom["type"] == "MultiPolygon" and coords:
            ring = coords[0][0] if coords[0] else []
        elif geom["type"] == "Polygon" and coords:
            ring = coords[0]
        else:
            ring = []

        if ring:
            # Simple centroid: average of coordinates
            lngs = [c[0] for c in ring]
            lats = [c[1] for c in ring]
            lng = sum(lngs) / len(lngs)
            lat = sum(lats) / len(lats)

    # Categorize property type from CAT and DESCPROP
    property_type = categorize_property(props)

    return {
        "span": props.get("SPAN") or props.get("GLIST_SPAN"),
        "address": props.get("E911ADDR"),
        "town": props.get("TOWN") or props.get("TNAME") or "Warren",
        "acres": props.get("ACRESGL"),
        "assessed_land": props.get("LAND_LV"),
        "assessed_building": props.get("IMPRV_LV"),
        "assessed_total": props.get("REAL_FLV"),
        "property_type": property_type,
        "year_built": None,  # Not in this dataset
        "lat": lat,
        "lng": lng,
        # Owner info
        "owner1": props.get("OWNER1"),
        "owner2": props.get("OWNER2"),
        "mailing_address": build_mailing_address(props),
        # Tax/homestead info
        "homestead_declared": props.get("HSDECL") == "Y",
        "housesite_value": props.get("HSITEVAL"),
        "description": props.get("DESCPROP"),
    }


def build_mailing_address(props: dict) -> str | None:
    """Build mailing address from components."""
    parts = []
    if props.get("ADDRGL1"):
        parts.append(props["ADDRGL1"])
    if props.get("ADDRGL2"):
        parts.append(props["ADDRGL2"])
    city_state_zip = []
    if props.get("CITYGL"):
        city_state_zip.append(props["CITYGL"])
    if props.get("STGL"):
        city_state_zip.append(props["STGL"])
    if props.get("ZIPGL"):
        city_state_zip.append(str(props["ZIPGL"]))
    if city_state_zip:
        parts.append(" ".join(city_state_zip))
    return ", ".join(parts) if parts else None


def categorize_property(props: dict) -> str:
    """Categorize property type from parcel properties."""
    cat = str(props.get("CAT", "") or "").upper()
    descr = str(props.get("DESCPROP", "") or "").lower()

    # CAT codes: R1 = single family, R2 = multi-family, etc.
    if cat.startswith("R"):
        if "1" in cat or "single" in descr:
            return "residential"
        elif "2" in cat or "multi" in descr or "duplex" in descr:
            return "multi-family"
        else:
            return "residential"
    elif cat.startswith("C"):
        return "commercial"
    elif cat.startswith("I"):
        return "industrial"
    elif "vacant" in descr or "land" in descr:
        return "land"
    else:
        return "other"


def import_parcels(dry_run: bool = False, test_only: bool = False):
    """Import all Warren parcels into the database."""
    init_db()

    # First, test with a single known parcel (488 Woods Road South)
    print("\n=== Testing with sample parcel (488 Woods Road South) ===")
    result = fetch_single_parcel("488 WOODS")

    if result.get("features"):
        feature = result["features"][0]
        parcel_data = parse_parcel(feature)
        print(f"\nFound parcel:")
        print(f"  SPAN: {parcel_data['span']}")
        print(f"  Address: {parcel_data['address']}")
        print(f"  Owner: {parcel_data['owner1']}")
        print(f"  Acres: {parcel_data['acres']}")
        print(f"  Land Value: ${parcel_data['assessed_land']:,}" if parcel_data['assessed_land'] else "  Land Value: N/A")
        print(f"  Building Value: ${parcel_data['assessed_building']:,}" if parcel_data['assessed_building'] else "  Building Value: N/A")
        print(f"  Total Value: ${parcel_data['assessed_total']:,}" if parcel_data['assessed_total'] else "  Total Value: N/A")
        print(f"  Type: {parcel_data['property_type']}")
        print(f"  Homestead: {'Yes' if parcel_data['homestead_declared'] else 'No'}")
        print(f"  Location: ({parcel_data['lat']:.6f}, {parcel_data['lng']:.6f})" if parcel_data['lat'] else "  Location: N/A")
    else:
        print("No parcel found for that address!")

    if test_only:
        return

    if dry_run:
        # Count total Warren parcels
        count_result = fetch_warren_parcels(limit=1)
        print(f"\n=== Dry run complete. Found parcels in Warren. ===")
        print("Use --import to actually import data.")
        return

    # Now fetch all Warren parcels
    print("\n=== Importing all Warren parcels ===")

    db = SessionLocal()
    total_imported = 0
    total_skipped = 0
    offset = 0

    try:
        while True:
            result = fetch_warren_parcels(offset=offset)
            features = result.get("features", [])

            if not features:
                break

            for feature in features:
                parcel_data = parse_parcel(feature)

                if not parcel_data.get("span"):
                    continue

                # Check if parcel exists
                existing = db.query(Parcel).filter(Parcel.span == parcel_data["span"]).first()
                if existing:
                    total_skipped += 1
                    continue

                # Create parcel
                parcel = Parcel(
                    span=parcel_data["span"],
                    address=parcel_data["address"],
                    town=parcel_data["town"],
                    acres=parcel_data["acres"],
                    assessed_land=parcel_data["assessed_land"],
                    assessed_building=parcel_data["assessed_building"],
                    assessed_total=parcel_data["assessed_total"],
                    property_type=parcel_data["property_type"],
                    lat=parcel_data["lat"],
                    lng=parcel_data["lng"],
                )
                db.add(parcel)
                db.flush()  # Get the parcel ID

                # Add owner if present
                if parcel_data.get("owner1"):
                    owner = Owner(
                        parcel_id=parcel.id,
                        name=parcel_data["owner1"],
                        mailing_address=parcel_data["mailing_address"],
                        is_primary=True,
                    )
                    db.add(owner)

                # Add second owner if present
                if parcel_data.get("owner2"):
                    owner2 = Owner(
                        parcel_id=parcel.id,
                        name=parcel_data["owner2"],
                        mailing_address=parcel_data["mailing_address"],
                        is_primary=False,
                    )
                    db.add(owner2)

                # Add tax status
                tax_status = TaxStatus(
                    parcel_id=parcel.id,
                    tax_year=2024,  # Current year from the data
                    homestead_filed=parcel_data["homestead_declared"],
                    housesite_value=parcel_data["housesite_value"],
                )
                db.add(tax_status)

                total_imported += 1

            db.commit()
            print(f"  Imported {total_imported} parcels so far (skipped {total_skipped} existing)...")

            # Check if we got fewer than requested (last page)
            if len(features) < 1000:
                break

            offset += len(features)

    finally:
        db.close()

    print(f"\n=== Import complete! ===")
    print(f"  {total_imported} parcels imported")
    print(f"  {total_skipped} existing parcels skipped")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Import Warren parcels from Vermont Geodata")
    parser.add_argument("--import", dest="do_import", action="store_true",
                        help="Actually import data (default is dry run)")
    parser.add_argument("--test", action="store_true",
                        help="Just test with sample parcel")
    args = parser.parse_args()

    import_parcels(dry_run=not args.do_import, test_only=args.test)
