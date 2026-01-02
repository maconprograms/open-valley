"""Import Short-Term Rental data from AirROI API.

This script implements the bronze → silver data pipeline for STR listings:
1. Fetch listings from AirROI API (paginated, 10 per page)
2. Store in bronze_str_listings table (raw, unmodified)
3. Transform via Pydantic models with spatial matching to parcels
4. Store in str_listings table (silver, linked to parcels)

Usage:
    uv run python scripts/import_airroi.py --fetch        # Fetch & import to bronze
    uv run python scripts/import_airroi.py --transform    # Transform bronze → silver
    uv run python scripts/import_airroi.py --all          # Full pipeline
    uv run python scripts/import_airroi.py --stats        # Show statistics
    uv run python scripts/import_airroi.py --towns        # Fetch all MRV towns
"""

import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime
from decimal import Decimal
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from src.database import engine
from src.models import (
    Base,
    Parcel,
    BronzeSTRListing,
    STRListing,
)
from src.transformations import (
    STRBronzeInput,
    STRSilverOutput,
    TransformationStats,
)


# =============================================================================
# Configuration
# =============================================================================

AIRROI_API_URL = "https://api.airroi.com/listings/search/market"
AIRROI_API_KEY = "3CPCtmGYXjasL46qLuaBL10ub0kFfvTeaC2dlsKM"

# Mad River Valley towns
MRV_TOWNS = ["Warren", "Waitsfield", "Fayston", "Moretown", "Duxbury"]

# Request delay to be respectful to API
REQUEST_DELAY_SECONDS = 0.5


# =============================================================================
# API Fetching
# =============================================================================


def fetch_airroi_page(
    city: str,
    state: str = "Vermont",
    offset: int = 0,
    page_size: int = 10,
) -> dict:
    """Fetch a page of listings from AirROI API."""
    payload = {
        "filter": {
            "city": {"eq": city},
            "state": {"eq": state}
        },
        "pagination": {
            "page_size": page_size,
            "offset": offset
        }
    }

    data = json.dumps(payload).encode('utf-8')

    request = urllib.request.Request(
        AIRROI_API_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "X-API-KEY": AIRROI_API_KEY
        }
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode())


def fetch_all_listings(city: str, state: str = "Vermont") -> list[dict]:
    """Fetch all listings for a city from AirROI API."""
    all_results = []
    offset = 0
    page_size = 10

    while True:
        print(f"  Fetching {city}: offset={offset}...")
        data = fetch_airroi_page(city, state, offset, page_size)

        results = data.get("results", [])
        if not results:
            break

        all_results.extend(results)

        # Check if there are more pages
        if len(results) < page_size:
            break

        offset += page_size
        time.sleep(REQUEST_DELAY_SECONDS)

    return all_results


# =============================================================================
# Bronze Layer: Raw Import
# =============================================================================


def import_to_bronze(session: Session, listings: list[dict], city: str) -> int:
    """Import raw AirROI listings to bronze table."""
    imported = 0
    skipped = 0

    for listing in listings:
        listing_info = listing.get("listing_info", {})
        host_info = listing.get("host_info", {})
        location = listing.get("location_info", {})
        props = listing.get("property_details", {})
        pricing = listing.get("pricing_info", {})
        ratings = listing.get("ratings", {})
        perf = listing.get("performance_metrics", {})

        listing_id = str(listing_info.get("listing_id", ""))
        if not listing_id:
            skipped += 1
            continue

        # Check if already exists
        existing = session.execute(
            select(BronzeSTRListing).where(
                BronzeSTRListing.platform == "airbnb",
                BronzeSTRListing.listing_id == listing_id
            )
        ).scalar_one_or_none()

        if existing:
            skipped += 1
            continue

        # Parse first review date
        first_review_date = None
        # AirROI doesn't provide first_review_date directly

        # Parse last review date from last_calendar_update if available
        last_review_date = None

        # Create bronze record
        record = BronzeSTRListing(
            platform="airbnb",
            listing_id=listing_id,
            listing_url=f"https://www.airbnb.com/rooms/{listing_id}",
            name=listing_info.get("listing_name"),
            property_type=listing_info.get("listing_type"),
            room_type=listing_info.get("room_type"),
            address=None,  # AirROI doesn't provide full address
            city=location.get("locality", city),
            state=location.get("region", "VT"),
            zip_code=location.get("district"),
            lat=Decimal(str(location.get("latitude"))) if location.get("latitude") else None,
            lng=Decimal(str(location.get("longitude"))) if location.get("longitude") else None,
            bedrooms=props.get("bedrooms"),
            bathrooms=Decimal(str(props.get("baths"))) if props.get("baths") else None,
            max_guests=props.get("guests"),
            price_per_night=Decimal(str(perf.get("ttm_avg_rate"))) if perf.get("ttm_avg_rate") else None,
            currency="USD",
            host_name=host_info.get("host_name"),
            host_id=str(host_info.get("host_id", "")),
            is_superhost=host_info.get("superhost"),
            total_reviews=ratings.get("num_reviews"),
            average_rating=Decimal(str(ratings.get("rating_overall"))) if ratings.get("rating_overall") else None,
            first_review_date=first_review_date,
            last_review_date=last_review_date,
            scraped_at=datetime.utcnow(),
            raw_json=json.dumps(listing),
            api_source="airroi",
        )

        session.add(record)
        imported += 1

    session.commit()
    return imported


# =============================================================================
# Silver Layer: Transformation with Spatial Matching
# =============================================================================


def find_nearest_parcel(
    session: Session,
    lat: Decimal,
    lng: Decimal,
    max_distance_meters: float = 200.0
) -> tuple[str | None, float | None]:
    """Find the nearest parcel to a given lat/lng.

    Returns (parcel_id, distance_meters) or (None, None) if no match within threshold.
    """
    result = session.execute(text("""
        SELECT
            id,
            (6371000 * acos(
                cos(radians(:lat)) * cos(radians(lat)) *
                cos(radians(lng) - radians(:lng)) +
                sin(radians(:lat)) * sin(radians(lat))
            )) as distance_m
        FROM parcels
        WHERE lat IS NOT NULL AND lng IS NOT NULL
        ORDER BY (lat - :lat)^2 + (lng - :lng)^2
        LIMIT 1
    """), {"lat": float(lat), "lng": float(lng)}).fetchone()

    if result and result[1] <= max_distance_meters:
        return str(result[0]), result[1]
    return None, None


def transform_bronze_to_silver(session: Session) -> TransformationStats:
    """Transform all unprocessed bronze STR records to silver."""
    stats = TransformationStats(source="bronze_str_listings")

    # Get bronze records that haven't been transformed yet
    subq = select(STRListing.bronze_id)
    bronze_records = session.execute(
        select(BronzeSTRListing).where(
            ~BronzeSTRListing.id.in_(subq),
            BronzeSTRListing.api_source == "airroi"  # Only AirROI records
        )
    ).scalars().all()

    print(f"  Processing {len(bronze_records)} bronze records...")

    for bronze in bronze_records:
        stats.records_processed += 1

        try:
            # Convert SQLAlchemy model to Pydantic input
            bronze_input = STRBronzeInput(
                id=bronze.id,
                platform=bronze.platform,
                listing_id=bronze.listing_id,
                listing_url=bronze.listing_url,
                name=bronze.name,
                property_type=bronze.property_type,
                room_type=bronze.room_type,
                address=bronze.address,
                city=bronze.city,
                state=bronze.state,
                zip_code=bronze.zip_code,
                lat=bronze.lat,
                lng=bronze.lng,
                bedrooms=bronze.bedrooms,
                bathrooms=bronze.bathrooms,
                max_guests=bronze.max_guests,
                price_per_night=bronze.price_per_night,
                currency=bronze.currency,
                host_name=bronze.host_name,
                host_id=bronze.host_id,
                is_superhost=bronze.is_superhost,
                total_reviews=bronze.total_reviews,
                average_rating=bronze.average_rating,
                first_review_date=bronze.first_review_date,
                last_review_date=bronze.last_review_date,
                scraped_at=bronze.scraped_at,
            )

            # Try to match to parcel via spatial centroid
            parcel_id = None
            match_method = None
            match_confidence = None

            if bronze.lat and bronze.lng:
                parcel_id, distance = find_nearest_parcel(session, bronze.lat, bronze.lng)
                if parcel_id:
                    match_method = "spatial_centroid"
                    # Confidence based on distance (0m = 1.0, 200m = 0.5)
                    match_confidence = max(0.5, 1.0 - (distance / 400.0))
                    stats.records_with_parcel_match += 1
                else:
                    stats.records_without_parcel_match += 1
            else:
                stats.records_without_parcel_match += 1

            # Transform with Pydantic validation
            silver = STRSilverOutput.from_bronze(
                bronze_input,
                parcel_id=parcel_id,
                match_method=match_method,
                match_confidence=match_confidence,
            )

            # Create silver record
            str_listing = STRListing(
                bronze_id=silver.bronze_id,
                parcel_id=silver.parcel_id,
                match_method=silver.match_method,
                match_confidence=silver.match_confidence,
                platform=silver.platform,
                listing_id=silver.listing_id,
                listing_url=silver.listing_url,
                name=silver.name,
                property_type=silver.property_type,
                lat=silver.lat,
                lng=silver.lng,
                bedrooms=silver.bedrooms,
                max_guests=silver.max_guests,
                price_per_night_usd=silver.price_per_night_usd,
                total_reviews=silver.total_reviews,
                average_rating=silver.average_rating,
                is_active=silver.is_active,
                validated_at=datetime.utcnow(),
            )

            session.add(str_listing)
            stats.records_valid += 1

        except Exception as e:
            stats.validation_errors.append(f"Listing {bronze.listing_id}: {str(e)}")
            stats.records_skipped += 1

    session.commit()
    return stats


# =============================================================================
# Statistics
# =============================================================================


def print_stats(session: Session):
    """Print statistics about the STR data."""
    # Bronze stats
    bronze_count = session.scalar(
        select(func.count(BronzeSTRListing.id)).where(
            BronzeSTRListing.api_source == "airroi"
        )
    )
    print(f"\n=== Bronze Layer: bronze_str_listings (AirROI) ===")
    print(f"Total records: {bronze_count:,}")

    # By city
    result = session.execute(text("""
        SELECT city, COUNT(*) as count
        FROM bronze_str_listings
        WHERE api_source = 'airroi'
        GROUP BY city
        ORDER BY count DESC
    """)).fetchall()

    print("\nBy city:")
    for row in result:
        print(f"  {row[0]}: {row[1]:,}")

    # Silver stats
    silver_count = session.scalar(select(func.count(STRListing.id)))
    matched_count = session.scalar(
        select(func.count(STRListing.id)).where(STRListing.parcel_id.isnot(None))
    )

    print(f"\n=== Silver Layer: str_listings ===")
    print(f"Total records: {silver_count:,}")
    if silver_count > 0:
        print(f"Matched to parcel: {matched_count:,} ({matched_count/silver_count*100:.1f}%)")

    # Sample matched listings with addresses
    print(f"\n=== Sample Matched Listings ===")
    result = session.execute(text("""
        SELECT
            s.name,
            s.bedrooms,
            s.price_per_night_usd / 100.0 as price,
            p.address,
            p.span,
            s.match_confidence
        FROM str_listings s
        JOIN parcels p ON s.parcel_id = p.id
        WHERE s.parcel_id IS NOT NULL
        ORDER BY s.match_confidence DESC
        LIMIT 10
    """)).fetchall()

    for row in result:
        name = row[0][:35] + "..." if row[0] and len(row[0]) > 35 else row[0]
        print(f"  {name}")
        print(f"    → {row[3]} (SPAN: {row[4]})")
        print(f"    {row[1]} bed, ${row[2]:.0f}/night, confidence: {row[5]:.2f}")


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(description="Import AirROI STR data")
    parser.add_argument("--fetch", action="store_true", help="Fetch from API to bronze")
    parser.add_argument("--transform", action="store_true", help="Transform bronze → silver")
    parser.add_argument("--all", action="store_true", help="Full pipeline")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--towns", action="store_true", help="Fetch all MRV towns (not just Warren)")
    parser.add_argument("--city", default="Warren", help="City to fetch (default: Warren)")
    args = parser.parse_args()

    if not (args.fetch or args.transform or args.all or args.stats):
        parser.print_help()
        return

    # Create tables if they don't exist
    print("Creating tables if needed...")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        if args.fetch or args.all:
            towns = MRV_TOWNS if args.towns else [args.city]

            for town in towns:
                print(f"\n=== Fetching AirROI listings for {town} ===")
                listings = fetch_all_listings(town)
                print(f"Fetched {len(listings)} listings")

                print(f"\n=== Importing to bronze layer ===")
                imported = import_to_bronze(session, listings, town)
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
