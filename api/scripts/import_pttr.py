"""Import Vermont Property Transfer Tax Returns (PTTR) data.

This script implements the bronze → silver data pipeline:
1. Fetch raw data from Vermont PTTR API (ArcGIS REST)
2. Store in bronze_pttr_transfers table (raw, unmodified)
3. Transform via Pydantic models with validation
4. Store in property_transfers table (silver, linked to parcels)

Usage:
    uv run python scripts/import_pttr.py --fetch        # Fetch & import to bronze
    uv run python scripts/import_pttr.py --transform    # Transform bronze → silver
    uv run python scripts/import_pttr.py --all          # Full pipeline
    uv run python scripts/import_pttr.py --stats        # Show statistics
"""

import argparse
import json
import sys
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from src.database import engine
from src.models import (
    Base,
    Parcel,
    BronzePTTRTransfer,
    PropertyTransfer,
)
from src.transformations import (
    PTTRBronzeInput,
    PTTRSilverOutput,
    TransformationStats,
    match_by_span,
)


# =============================================================================
# Configuration
# =============================================================================

# ArcGIS Online endpoint (VT Open Geodata Portal)
PTTR_API_BASE = "https://services1.arcgis.com/BkFxaEFNwHqX3tAw/arcgis/rest/services/FS_VCGI_OPENDATA_Cadastral_PTTR_point_WM_v1_view/FeatureServer/0"

# Fields to fetch from API (based on actual API metadata)
PTTR_FIELDS = [
    "OBJECTID",
    "span",               # SPAN identifier
    "TownSpan",           # Alternative SPAN
    "propLocStr",         # Property location street
    "propLocCty",         # Property location city (town)
    "TOWNNAME",           # Town name for filtering
    "ValPdOrTrn",         # Value paid or transferred (sale price)
    "closeDate",          # Transfer/closing date
    "postedDate",         # Posted date
    "sellEntNam",         # Seller entity name
    "sellLstNam",         # Seller last name
    "sellFstNam",         # Seller first name
    "sellerSt",           # Seller state
    "buyEntNam",          # Buyer entity name
    "buyLstNam",          # Buyer last name
    "buyFstNam",          # Buyer first name
    "buyerState",         # Buyer state
    "buyerZip",           # Buyer zip
    "bUsePrDesc",         # Buyer intended use description
    "intPrpType",         # Intended property type
    "Latitude",
    "Longitude",
]


# =============================================================================
# API Fetching
# =============================================================================


def fetch_pttr_page(
    where: str = "TOWNNAME = 'Warren'",
    offset: int = 0,
    limit: int = 1000,
) -> dict:
    """Fetch a page of PTTR records from the ArcGIS API."""
    params = {
        "where": where,
        "outFields": ",".join(PTTR_FIELDS),
        "returnGeometry": "true",
        "resultOffset": str(offset),
        "resultRecordCount": str(limit),
        "f": "json",
    }

    url = f"{PTTR_API_BASE}/query?{urllib.parse.urlencode(params)}"
    print(f"  Fetching: offset={offset}, limit={limit}")

    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode())


def fetch_all_pttr(where: str = "TOWNNAME = 'Warren'") -> list[dict]:
    """Fetch all PTTR records matching the query."""
    all_features = []
    offset = 0
    limit = 1000

    while True:
        data = fetch_pttr_page(where=where, offset=offset, limit=limit)
        features = data.get("features", [])

        if not features:
            break

        all_features.extend(features)
        print(f"  Fetched {len(all_features)} total records...")

        # Check if there are more records
        if len(features) < limit:
            break

        offset += limit

    return all_features


# =============================================================================
# Bronze Layer: Raw Import
# =============================================================================


def import_to_bronze(session: Session, features: list[dict]) -> int:
    """Import raw PTTR features to bronze table."""
    imported = 0
    skipped = 0

    for feature in features:
        attrs = feature.get("attributes", {})
        geom = feature.get("geometry", {})

        objectid = attrs.get("OBJECTID")
        if not objectid:
            skipped += 1
            continue

        # Check if already exists
        existing = session.execute(
            select(BronzePTTRTransfer).where(BronzePTTRTransfer.objectid == objectid)
        ).scalar_one_or_none()

        if existing:
            skipped += 1
            continue

        # Parse transfer date (ArcGIS uses epoch milliseconds)
        transfer_date = None
        if attrs.get("closeDate"):
            try:
                transfer_date = datetime.fromtimestamp(attrs["closeDate"] / 1000)
            except (ValueError, TypeError):
                pass

        # Build buyer name from components
        buyer_name_parts = [
            attrs.get("buyEntNam"),
            f"{attrs.get('buyFstNam', '')} {attrs.get('buyLstNam', '')}".strip()
        ]
        buyer_name = " / ".join([p for p in buyer_name_parts if p])

        # Build seller name from components
        seller_name_parts = [
            attrs.get("sellEntNam"),
            f"{attrs.get('sellFstNam', '')} {attrs.get('sellLstNam', '')}".strip()
        ]
        seller_name = " / ".join([p for p in seller_name_parts if p])

        # Use span or TownSpan as fallback
        span = attrs.get("span") or attrs.get("TownSpan")

        # Sale price from ValPdOrTrn (Value Paid or Transferred)
        sale_price = attrs.get("ValPdOrTrn")
        if sale_price:
            sale_price = int(sale_price)

        # Create bronze record
        record = BronzePTTRTransfer(
            objectid=objectid,
            globalid=None,  # Not in this API
            span=span,
            property_address=attrs.get("propLocStr"),
            town=attrs.get("TOWNNAME") or attrs.get("propLocCty"),
            sale_price=sale_price,
            transfer_date=transfer_date,
            transfer_type=None,  # Not directly available
            buyer_name=buyer_name or None,
            buyer_state=attrs.get("buyerState"),
            buyer_zip=attrs.get("buyerZip"),
            seller_name=seller_name or None,
            intended_use=attrs.get("bUsePrDesc"),
            property_type_code=attrs.get("intPrpType"),
            lat=attrs.get("Latitude"),
            lng=attrs.get("Longitude"),
            raw_json=json.dumps(feature),
            fetched_at=datetime.utcnow(),
            api_source="vcgi_pttr_arcgis_online",
        )

        session.add(record)
        imported += 1

    session.commit()
    return imported


# =============================================================================
# Silver Layer: Transformation
# =============================================================================


def build_span_lookup(session: Session) -> dict[str, str]:
    """Build SPAN → parcel_id lookup dictionary."""
    result = session.execute(select(Parcel.span, Parcel.id))
    # Normalize SPANs for matching
    return {
        row.span.strip().upper().replace("-", "").replace(" ", ""): str(row.id)
        for row in result
        if row.span
    }


def transform_bronze_to_silver(session: Session) -> TransformationStats:
    """Transform all unprocessed bronze records to silver."""
    stats = TransformationStats(source="bronze_pttr_transfers")

    # Build parcel lookup
    print("  Building SPAN → parcel lookup...")
    span_lookup = build_span_lookup(session)
    print(f"  Found {len(span_lookup)} parcels with SPANs")

    # Get bronze records that haven't been transformed yet
    # (no corresponding silver record with same bronze_id)
    subq = select(PropertyTransfer.bronze_id)
    bronze_records = session.execute(
        select(BronzePTTRTransfer).where(
            ~BronzePTTRTransfer.id.in_(subq)
        )
    ).scalars().all()

    print(f"  Processing {len(bronze_records)} bronze records...")

    for bronze in bronze_records:
        stats.records_processed += 1

        try:
            # Convert SQLAlchemy model to Pydantic input
            bronze_input = PTTRBronzeInput(
                id=bronze.id,
                objectid=bronze.objectid,
                span=bronze.span,
                property_address=bronze.property_address,
                town=bronze.town,
                sale_price=bronze.sale_price,
                transfer_date=bronze.transfer_date,
                transfer_type=bronze.transfer_type,
                buyer_name=bronze.buyer_name,
                buyer_state=bronze.buyer_state,
                buyer_zip=bronze.buyer_zip,
                seller_name=bronze.seller_name,
                intended_use=bronze.intended_use,
                property_type_code=bronze.property_type_code,
                lat=bronze.lat,
                lng=bronze.lng,
            )

            # Try to match to parcel
            parcel_id = None
            if bronze.span:
                match = match_by_span(bronze.span, span_lookup)
                if match.parcel_id:
                    parcel_id = match.parcel_id
                    stats.records_with_parcel_match += 1
                else:
                    stats.records_without_parcel_match += 1

            # Transform with Pydantic validation
            silver = PTTRSilverOutput.from_bronze(bronze_input, parcel_id)

            if silver is None:
                stats.records_skipped += 1
                continue

            # Create silver record
            transfer = PropertyTransfer(
                bronze_id=silver.bronze_id,
                parcel_id=silver.parcel_id,
                span=silver.span,
                sale_price=silver.sale_price,
                transfer_date=silver.transfer_date,
                transfer_type=silver.transfer_type,
                buyer_name=silver.buyer_name,
                buyer_state=silver.buyer_state,
                is_out_of_state_buyer=silver.is_out_of_state_buyer,
                seller_name=silver.seller_name,
                intended_use=silver.intended_use,
                is_primary_residence=silver.is_primary_residence,
                is_secondary_residence=silver.is_secondary_residence,
                validated_at=datetime.utcnow(),
                validation_notes=silver.validation_notes,
            )

            session.add(transfer)
            stats.records_valid += 1

        except Exception as e:
            stats.validation_errors.append(f"Record {bronze.objectid}: {str(e)}")
            stats.records_skipped += 1

    session.commit()
    return stats


# =============================================================================
# Statistics
# =============================================================================


def print_stats(session: Session):
    """Print statistics about the PTTR data."""
    # Bronze stats
    bronze_count = session.scalar(select(func.count(BronzePTTRTransfer.id)))
    print(f"\n=== Bronze Layer: bronze_pttr_transfers ===")
    print(f"Total records: {bronze_count:,}")

    # Silver stats
    silver_count = session.scalar(select(func.count(PropertyTransfer.id)))
    matched_count = session.scalar(
        select(func.count(PropertyTransfer.id)).where(PropertyTransfer.parcel_id.isnot(None))
    )
    out_of_state = session.scalar(
        select(func.count(PropertyTransfer.id)).where(PropertyTransfer.is_out_of_state_buyer == True)
    )
    secondary = session.scalar(
        select(func.count(PropertyTransfer.id)).where(PropertyTransfer.is_secondary_residence == True)
    )

    print(f"\n=== Silver Layer: property_transfers ===")
    print(f"Total records: {silver_count:,}")
    if silver_count > 0:
        print(f"Matched to parcel: {matched_count:,} ({matched_count/silver_count*100:.1f}%)")
        print(f"Out-of-state buyers: {out_of_state:,} ({out_of_state/silver_count*100:.1f}%)")
        print(f"Secondary residence: {secondary:,} ({secondary/silver_count*100:.1f}%)")

    # Year breakdown
    print(f"\n=== Transfers by Year ===")
    result = session.execute(text("""
        SELECT
            EXTRACT(YEAR FROM transfer_date) as year,
            COUNT(*) as count,
            SUM(sale_price) as total_value,
            AVG(sale_price)::int as avg_price,
            SUM(CASE WHEN is_out_of_state_buyer THEN 1 ELSE 0 END) as out_of_state,
            SUM(CASE WHEN is_secondary_residence THEN 1 ELSE 0 END) as secondary
        FROM property_transfers
        WHERE transfer_date IS NOT NULL
        GROUP BY EXTRACT(YEAR FROM transfer_date)
        ORDER BY year DESC
        LIMIT 10
    """))

    for row in result:
        print(f"  {int(row.year)}: {row.count:>4} transfers, "
              f"${row.total_value/1_000_000:.1f}M total, "
              f"${row.avg_price:>7,} avg, "
              f"{row.out_of_state/row.count*100:.0f}% out-of-state, "
              f"{row.secondary/row.count*100:.0f}% secondary")


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(description="Import PTTR data")
    parser.add_argument("--fetch", action="store_true", help="Fetch from API to bronze")
    parser.add_argument("--transform", action="store_true", help="Transform bronze → silver")
    parser.add_argument("--all", action="store_true", help="Full pipeline")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--town", default="WARREN", help="Town to fetch (default: WARREN)")
    args = parser.parse_args()

    if not (args.fetch or args.transform or args.all or args.stats):
        parser.print_help()
        return

    # Create tables if they don't exist
    print("Creating tables if needed...")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        if args.fetch or args.all:
            print(f"\n=== Fetching PTTR data for {args.town} ===")
            features = fetch_all_pttr(where=f"TOWNNAME = '{args.town}'")
            print(f"Fetched {len(features)} features")

            print("\n=== Importing to bronze layer ===")
            imported = import_to_bronze(session, features)
            print(f"Imported {imported} new records to bronze")

        if args.transform or args.all:
            print("\n=== Transforming bronze → silver ===")
            stats = transform_bronze_to_silver(session)
            print(f"Processed: {stats.records_processed}")
            print(f"Valid: {stats.records_valid}")
            print(f"Skipped: {stats.records_skipped}")
            print(f"Matched to parcel: {stats.records_with_parcel_match}")
            print(f"No parcel match: {stats.records_without_parcel_match}")
            if stats.validation_errors:
                print(f"Errors ({len(stats.validation_errors)}):")
                for err in stats.validation_errors[:5]:
                    print(f"  - {err}")

        if args.stats or args.all:
            print_stats(session)


if __name__ == "__main__":
    main()
