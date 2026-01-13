"""Import Short-Term Rental (STR) listings from Apify scrapers.

This script implements the bronze → silver data pipeline for STR data:
1. Read JSON output from Apify scraper runs (Airbnb/VRBO)
2. Store in bronze_str_listings table (raw, unmodified)
3. Match to parcels via spatial join (PostGIS ST_Contains)
4. Store in str_listings table (silver, linked to parcels)

Usage:
    uv run python scripts/import_str.py --import data/str/*.json  # Import JSON files
    uv run python scripts/import_str.py --transform               # Transform bronze → silver
    uv run python scripts/import_str.py --stats                   # Show statistics

Note: To get STR data, use Apify scrapers:
    - Airbnb: https://apify.com/dtrungtin/airbnb-scraper
    - VRBO: https://apify.com/vacasa/vrbo-scraper

Search for listings in Warren/Mad River Valley area and download results as JSON.
"""

import argparse
import json
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

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
# JSON Parsing - Handle different scraper output formats
# =============================================================================


def parse_airbnb_listing(data: dict) -> dict:
    """Normalize Airbnb scraper output to our bronze schema."""
    # Airbnb scraper typically returns:
    # id, url, name, roomType, lat, lng, bedrooms, bathrooms, guests, price, etc.
    return {
        "platform": "airbnb",
        "listing_id": str(data.get("id") or data.get("listing_id") or data.get("roomId")),
        "listing_url": data.get("url") or data.get("listing_url"),
        "name": data.get("name") or data.get("title"),
        "property_type": data.get("roomType") or data.get("room_type") or data.get("propertyType"),
        "room_type": data.get("roomType") or data.get("room_type"),
        "address": data.get("address") or data.get("publicAddress"),
        "city": data.get("city") or data.get("location", {}).get("city"),
        "state": data.get("state") or data.get("location", {}).get("state"),
        "zip_code": data.get("zipcode") or data.get("zip_code"),
        "lat": data.get("lat") or data.get("latitude") or (data.get("location", {}) or {}).get("lat"),
        "lng": data.get("lng") or data.get("longitude") or (data.get("location", {}) or {}).get("lng"),
        "bedrooms": data.get("bedrooms") or data.get("bedroomCount"),
        "bathrooms": data.get("bathrooms") or data.get("bathroomCount"),
        "max_guests": data.get("guests") or data.get("personCapacity") or data.get("maxGuests"),
        "price_per_night": data.get("price") or data.get("pricing", {}).get("rate"),
        "currency": data.get("currency") or "USD",
        "host_name": data.get("hostName") or (data.get("host", {}) or {}).get("name"),
        "host_id": str(data.get("hostId") or (data.get("host", {}) or {}).get("id") or ""),
        "is_superhost": data.get("isSuperhost") or (data.get("host", {}) or {}).get("isSuperHost"),
        "total_reviews": data.get("reviews") or data.get("reviewsCount") or data.get("numberOfReviews"),
        "average_rating": data.get("rating") or data.get("starRating") or data.get("guestSatisfactionOverall"),
        "first_review_date": None,  # Rarely available
        "last_review_date": None,  # Rarely available
        "raw_json": data,
    }


def parse_vrbo_listing(data: dict) -> dict:
    """Normalize VRBO scraper output to our bronze schema."""
    # VRBO scraper typically has different field names
    return {
        "platform": "vrbo",
        "listing_id": str(data.get("propertyId") or data.get("id") or data.get("listingId")),
        "listing_url": data.get("url") or data.get("detailPageUrl"),
        "name": data.get("headline") or data.get("name") or data.get("title"),
        "property_type": data.get("propertyType"),
        "room_type": data.get("roomType") or data.get("propertyType"),
        "address": data.get("address") or data.get("streetAddress"),
        "city": data.get("city") or (data.get("location", {}) or {}).get("city"),
        "state": data.get("state") or (data.get("location", {}) or {}).get("state"),
        "zip_code": data.get("postalCode") or data.get("zipCode"),
        "lat": data.get("latitude") or (data.get("geoLocation", {}) or {}).get("latitude"),
        "lng": data.get("longitude") or (data.get("geoLocation", {}) or {}).get("longitude"),
        "bedrooms": data.get("bedrooms"),
        "bathrooms": data.get("bathrooms"),
        "max_guests": data.get("sleeps") or data.get("maxOccupancy"),
        "price_per_night": data.get("pricePerNight") or data.get("averagePrice"),
        "currency": data.get("currency") or "USD",
        "host_name": data.get("hostName") or (data.get("owner", {}) or {}).get("name"),
        "host_id": str(data.get("hostId") or (data.get("owner", {}) or {}).get("id") or ""),
        "is_superhost": None,  # VRBO uses "Premier Host"
        "total_reviews": data.get("reviewCount") or data.get("numberOfReviews"),
        "average_rating": data.get("averageRating") or data.get("rating"),
        "first_review_date": None,
        "last_review_date": None,
        "raw_json": data,
    }


def detect_platform(data: dict) -> str:
    """Detect which platform a listing came from."""
    url = data.get("url") or data.get("listing_url") or data.get("detailPageUrl") or ""
    if "airbnb" in url.lower():
        return "airbnb"
    if "vrbo" in url.lower() or "homeaway" in url.lower():
        return "vrbo"
    # Check for platform-specific fields
    if data.get("roomId") or data.get("isSuperhost") or "airbnb" in str(data.get("id", "")).lower():
        return "airbnb"
    if data.get("propertyId") or data.get("sleeps"):
        return "vrbo"
    return "unknown"


def parse_listing(data: dict) -> dict | None:
    """Parse a listing from either platform."""
    platform = detect_platform(data)
    if platform == "airbnb":
        return parse_airbnb_listing(data)
    elif platform == "vrbo":
        return parse_vrbo_listing(data)
    else:
        print(f"  Warning: Unknown platform for listing {data.get('id')}")
        return None


# =============================================================================
# Bronze Layer: Raw Import
# =============================================================================


def import_json_to_bronze(session: Session, json_file: Path, scraper_run_id: str | None = None) -> int:
    """Import a JSON file of STR listings to bronze table."""
    with open(json_file) as f:
        data = json.load(f)

    # Handle both array and object responses
    if isinstance(data, dict):
        listings = data.get("results", []) or data.get("items", []) or [data]
    else:
        listings = data

    imported = 0
    skipped = 0

    for item in listings:
        parsed = parse_listing(item)
        if not parsed:
            skipped += 1
            continue

        platform = parsed["platform"]
        listing_id = parsed["listing_id"]

        if not listing_id:
            skipped += 1
            continue

        # Check if already exists
        existing = session.execute(
            select(BronzeSTRListing).where(
                BronzeSTRListing.platform == platform,
                BronzeSTRListing.listing_id == listing_id,
            )
        ).scalar_one_or_none()

        if existing:
            # Update last_seen
            skipped += 1
            continue

        # Parse price
        price = parsed.get("price_per_night")
        if price and isinstance(price, str):
            price = float(price.replace("$", "").replace(",", ""))
        elif price:
            price = float(price)

        record = BronzeSTRListing(
            platform=platform,
            listing_id=listing_id,
            listing_url=parsed.get("listing_url"),
            name=parsed.get("name"),
            property_type=parsed.get("property_type"),
            room_type=parsed.get("room_type"),
            address=parsed.get("address"),
            city=parsed.get("city"),
            state=parsed.get("state"),
            zip_code=parsed.get("zip_code"),
            lat=Decimal(str(parsed["lat"])) if parsed.get("lat") else None,
            lng=Decimal(str(parsed["lng"])) if parsed.get("lng") else None,
            bedrooms=parsed.get("bedrooms"),
            bathrooms=Decimal(str(parsed["bathrooms"])) if parsed.get("bathrooms") else None,
            max_guests=parsed.get("max_guests"),
            price_per_night=Decimal(str(price)) if price else None,
            currency=parsed.get("currency", "USD"),
            host_name=parsed.get("host_name"),
            host_id=parsed.get("host_id"),
            is_superhost=parsed.get("is_superhost"),
            total_reviews=parsed.get("total_reviews"),
            average_rating=Decimal(str(parsed["average_rating"])) if parsed.get("average_rating") else None,
            first_review_date=None,
            last_review_date=None,
            raw_json=json.dumps(parsed["raw_json"]),
            scraped_at=datetime.utcnow(),
            scraper_run_id=scraper_run_id,
        )

        session.add(record)
        imported += 1

    session.commit()
    return imported


# =============================================================================
# Silver Layer: Spatial Matching
# =============================================================================


def match_listing_to_parcel(session: Session, lat: float, lng: float) -> tuple[str | None, str | None, float | None]:
    """Match a coordinate to a parcel using PostGIS spatial functions.

    First tries ST_Contains with parcel geometry polygons.
    Falls back to point-to-point distance matching using parcel centroids.
    """
    if not lat or not lng:
        return None, None, None

    # Try 1: Use ST_Contains if parcels have geometry polygons
    result = session.execute(text("""
        SELECT id, span
        FROM parcels
        WHERE geometry IS NOT NULL
          AND ST_Contains(geometry, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
        LIMIT 1
    """), {"lat": lat, "lng": lng}).fetchone()

    if result:
        return str(result.id), "spatial", 0.95  # High confidence for polygon match

    # Try 2: Point-to-point distance matching using parcel lat/lng centroids
    # This works when we have parcel coordinates but not full geometry
    result = session.execute(text("""
        SELECT id, span,
            ST_Distance(
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                ST_SetSRID(ST_MakePoint(lng::float, lat::float), 4326)::geography
            ) as distance_m
        FROM parcels
        WHERE lat IS NOT NULL AND lng IS NOT NULL
        ORDER BY distance_m
        LIMIT 1
    """), {"lat": lat, "lng": lng}).fetchone()

    if result and result.distance_m <= 200:  # Within 200m threshold
        # Confidence decreases with distance
        # 0m = 0.95, 100m = 0.70, 200m = 0.45
        confidence = max(0.45, 0.95 - (result.distance_m / 200))
        return str(result.id), "spatial_centroid", confidence

    return None, None, None


def transform_bronze_to_silver(session: Session) -> TransformationStats:
    """Transform all unprocessed bronze STR records to silver."""
    stats = TransformationStats(source="bronze_str_listings")

    # Get bronze records that haven't been transformed yet
    subq = select(STRListing.bronze_id)
    bronze_records = session.execute(
        select(BronzeSTRListing).where(
            ~BronzeSTRListing.id.in_(subq)
        )
    ).scalars().all()

    print(f"  Processing {len(bronze_records)} bronze STR listings...")

    for bronze in bronze_records:
        stats.records_processed += 1

        try:
            # Match to parcel via spatial join
            parcel_id = None
            match_method = None
            match_confidence = None

            if bronze.lat and bronze.lng:
                parcel_id, match_method, match_confidence = match_listing_to_parcel(
                    session, float(bronze.lat), float(bronze.lng)
                )

            if parcel_id:
                stats.records_with_parcel_match += 1
            else:
                stats.records_without_parcel_match += 1

            # Determine if active (reviews in last year)
            is_active = True
            if bronze.last_review_date:
                days_since_review = (datetime.utcnow() - bronze.last_review_date).days
                is_active = days_since_review < 365

            # Convert price to cents for precision
            price_cents = None
            if bronze.price_per_night:
                price_cents = int(float(bronze.price_per_night) * 100)

            # Create silver record
            listing = STRListing(
                bronze_id=bronze.id,
                parcel_id=parcel_id,
                match_method=match_method,
                match_confidence=Decimal(str(match_confidence)) if match_confidence else None,
                platform=bronze.platform,
                listing_id=bronze.listing_id,
                listing_url=bronze.listing_url,
                name=bronze.name,
                property_type=bronze.property_type,
                lat=bronze.lat,
                lng=bronze.lng,
                bedrooms=bronze.bedrooms,
                max_guests=bronze.max_guests,
                price_per_night_usd=price_cents,
                total_reviews=bronze.total_reviews,
                average_rating=bronze.average_rating,
                is_active=is_active,
                validated_at=datetime.utcnow(),
                last_seen_at=datetime.utcnow(),
            )

            session.add(listing)
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
    """Print statistics about STR data."""
    # Bronze stats
    bronze_count = session.scalar(select(func.count(BronzeSTRListing.id)))
    print(f"\n=== Bronze Layer: bronze_str_listings ===")
    print(f"Total records: {bronze_count:,}")

    if bronze_count > 0:
        # Platform breakdown
        result = session.execute(text("""
            SELECT platform, COUNT(*) as count
            FROM bronze_str_listings
            GROUP BY platform
        """))
        for row in result:
            print(f"  {row.platform}: {row.count:,}")

    # Silver stats
    silver_count = session.scalar(select(func.count(STRListing.id)))
    matched_count = session.scalar(
        select(func.count(STRListing.id)).where(STRListing.parcel_id.isnot(None))
    )
    active_count = session.scalar(
        select(func.count(STRListing.id)).where(STRListing.is_active == True)
    )

    print(f"\n=== Silver Layer: str_listings ===")
    print(f"Total records: {silver_count:,}")
    if silver_count > 0:
        print(f"Matched to parcel: {matched_count:,} ({matched_count/silver_count*100:.1f}%)")
        print(f"Active listings: {active_count:,} ({active_count/silver_count*100:.1f}%)")

        # Bedroom distribution
        result = session.execute(text("""
            SELECT
                COALESCE(bedrooms, 0) as beds,
                COUNT(*) as count,
                AVG(price_per_night_usd/100.0)::int as avg_price
            FROM str_listings
            GROUP BY COALESCE(bedrooms, 0)
            ORDER BY beds
            LIMIT 10
        """))
        print("\n  By Bedrooms:")
        for row in result:
            print(f"    {row.beds} BR: {row.count:>3} listings, ${row.avg_price or 0:>3}/night avg")


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(description="Import STR listings from Apify")
    parser.add_argument("--import", dest="import_files", nargs="+", metavar="FILE",
                        help="JSON files to import to bronze")
    parser.add_argument("--transform", action="store_true", help="Transform bronze → silver")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--run-id", help="Scraper run ID for tracking")
    args = parser.parse_args()

    if not (args.import_files or args.transform or args.stats):
        parser.print_help()
        return

    # Create tables if they don't exist
    print("Creating tables if needed...")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        if args.import_files:
            print(f"\n=== Importing {len(args.import_files)} JSON files ===")
            total_imported = 0
            for filepath in args.import_files:
                path = Path(filepath)
                if not path.exists():
                    print(f"  Warning: {filepath} not found, skipping")
                    continue

                print(f"  Importing {path.name}...")
                imported = import_json_to_bronze(session, path, args.run_id)
                print(f"    Imported {imported} listings")
                total_imported += imported

            print(f"\nTotal imported: {total_imported}")

        if args.transform:
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

        if args.stats:
            print_stats(session)


if __name__ == "__main__":
    main()
