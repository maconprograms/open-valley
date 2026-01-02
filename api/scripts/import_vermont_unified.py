"""Unified Vermont Parcel + Dwelling + Owner Import.

This script properly imports Vermont's parcel data, handling condo units correctly:
- Each unique SPAN becomes a Parcel
- Each API row becomes a Dwelling (condo units share SPAN but are separate dwellings)
- Each owner becomes a Person or Organization
- PropertyOwnership links dwellings to their owners

This replaces the old import_parcels.py + infer_dwellings.py workflow.

Usage:
    uv run python scripts/import_vermont_unified.py --fetch     # Fetch from API
    uv run python scripts/import_vermont_unified.py --import    # Import to database
    uv run python scripts/import_vermont_unified.py --all       # Full pipeline
    uv run python scripts/import_vermont_unified.py --stats     # Show statistics
    uv run python scripts/import_vermont_unified.py --test      # Test with Bridges
"""

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Iterator
from uuid import uuid4

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, delete, func, select, text
from sqlalchemy.orm import Session

from src.database import engine
from src.models import (
    Base,
    Dwelling,
    Organization,
    OrganizationType,
    OwnershipType,
    Parcel,
    Person,
    PropertyOwnership,
)


# =============================================================================
# Configuration
# =============================================================================

ARCGIS_BASE = "https://services1.arcgis.com/BkFxaEFNwHqX3tAw/arcgis/rest/services"
PARCELS_LAYER = "FS_VCGI_OPENDATA_Cadastral_VTPARCELS_poly_standardized_parcels_SP_v1/FeatureServer/0"
PARCELS_URL = f"{ARCGIS_BASE}/{PARCELS_LAYER}/query"

TOWN = "WARREN"
PAGE_SIZE = 1000


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class VermontRow:
    """Single row from Vermont's parcel API."""
    span: str
    address: str | None
    owner_name: str | None
    owner2_name: str | None
    mailing_address: str | None
    mailing_city: str | None
    mailing_state: str | None
    mailing_zip: str | None
    acres: float | None
    assessed_land: int | None
    assessed_building: int | None
    assessed_total: int | None
    cat_code: str | None
    descprop: str | None
    homestead_declared: bool
    housesite_value: int | None
    lat: float | None
    lng: float | None
    geometry: dict | None


@dataclass
class ParsedOwner:
    """Result of parsing an owner name."""
    is_organization: bool
    org_type: str | None  # 'llc', 'trust', 'corporation', etc.
    first_name: str | None
    last_name: str | None
    suffix: str | None
    raw_name: str


# =============================================================================
# API Fetching
# =============================================================================

def fetch_page(offset: int = 0) -> list[dict]:
    """Fetch a page of parcel data from Vermont API."""
    params = {
        "where": f"TOWN = '{TOWN}'",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "json",
        "resultOffset": offset,
        "resultRecordCount": PAGE_SIZE,
    }

    url = PARCELS_URL + "?" + urllib.parse.urlencode(params)

    with urllib.request.urlopen(url, timeout=60) as response:
        data = json.loads(response.read().decode())
        return data.get("features", [])


def fetch_all_rows() -> Iterator[VermontRow]:
    """Fetch all rows from Vermont API with pagination."""
    offset = 0
    total = 0

    while True:
        print(f"  Fetching offset {offset}...")
        features = fetch_page(offset)

        if not features:
            break

        for f in features:
            row = parse_feature(f)
            if row and row.span:
                yield row
                total += 1

        if len(features) < PAGE_SIZE:
            break

        offset += PAGE_SIZE

    print(f"  Fetched {total} total rows")


def parse_feature(feature: dict) -> VermontRow | None:
    """Parse an API feature into a VermontRow."""
    attrs = feature.get("attributes", {})
    geom = feature.get("geometry")

    span = attrs.get("SPAN") or attrs.get("GLIST_SPAN")
    if not span:
        return None

    # Calculate centroid from geometry
    lat, lng = None, None
    if geom and geom.get("rings"):
        rings = geom["rings"]
        if rings and rings[0]:
            coords = rings[0]
            lngs = [c[0] for c in coords]
            lats = [c[1] for c in coords]
            lng = sum(lngs) / len(lngs)
            lat = sum(lats) / len(lats)

    # Build mailing address
    mailing_parts = [
        attrs.get("ADDRGL1"),
        attrs.get("ADDRGL2"),
    ]
    mailing_address = ", ".join(p for p in mailing_parts if p)

    return VermontRow(
        span=span,
        address=attrs.get("E911ADDR"),
        owner_name=attrs.get("OWNER1"),
        owner2_name=attrs.get("OWNER2"),
        mailing_address=mailing_address or None,
        mailing_city=attrs.get("CITYGL"),
        mailing_state=attrs.get("STGL"),
        mailing_zip=attrs.get("ZIPGL"),
        acres=attrs.get("ACRESGL"),
        assessed_land=attrs.get("LAND_LV"),
        assessed_building=attrs.get("IMPRV_LV"),
        assessed_total=attrs.get("REAL_FLV"),
        cat_code=attrs.get("CAT"),
        descprop=attrs.get("DESCPROP"),
        homestead_declared=attrs.get("HSDECL") == "Y",
        housesite_value=attrs.get("HSITEVAL"),
        lat=lat,
        lng=lng,
        geometry=geom,
    )


# =============================================================================
# Owner Parsing
# =============================================================================

# Patterns for detecting organizations
LLC_PATTERN = re.compile(r'\bLLC\b|\bL\.L\.C\b', re.IGNORECASE)
TRUST_PATTERN = re.compile(r'\bTRUST\b|\bTRUSTEE\b', re.IGNORECASE)
CORP_PATTERN = re.compile(r'\bINC\b|\bCORP\b|\bCORPORATION\b', re.IGNORECASE)
ESTATE_PATTERN = re.compile(r'\bESTATE\b', re.IGNORECASE)
SUFFIXES = {"JR", "SR", "II", "III", "IV", "V"}


def parse_owner_name(raw_name: str | None) -> ParsedOwner | None:
    """Parse a Grand List owner name into Person or Organization.

    Examples:
    - "PHILLIPS III ROBERT M" → Person(last=Phillips, first=Robert, suffix=III)
    - "MAD RIVER LLC" → Organization(type=llc)
    - "WESTON STACEY B REVOCABLE TRUST" → Organization(type=trust)
    """
    if not raw_name:
        return None

    name = raw_name.strip()
    if not name:
        return None

    # Check for organization patterns
    if LLC_PATTERN.search(name):
        return ParsedOwner(
            is_organization=True,
            org_type="llc",
            first_name=None,
            last_name=None,
            suffix=None,
            raw_name=name,
        )

    if CORP_PATTERN.search(name):
        return ParsedOwner(
            is_organization=True,
            org_type="corporation",
            first_name=None,
            last_name=None,
            suffix=None,
            raw_name=name,
        )

    if TRUST_PATTERN.search(name):
        return ParsedOwner(
            is_organization=True,
            org_type="trust",
            first_name=None,
            last_name=None,
            suffix=None,
            raw_name=name,
        )

    if ESTATE_PATTERN.search(name):
        return ParsedOwner(
            is_organization=True,
            org_type="estate",
            first_name=None,
            last_name=None,
            suffix=None,
            raw_name=name,
        )

    # Parse as person: "LASTNAME [SUFFIX] FIRSTNAME [MIDDLE]"
    tokens = name.split()
    if not tokens:
        return None

    # Remove any trailing ampersand and second person (handle elsewhere)
    if "&" in tokens:
        amp_idx = tokens.index("&")
        tokens = tokens[:amp_idx]

    if not tokens:
        return None

    last_name = tokens[0].title()
    first_name = None
    suffix = None

    if len(tokens) >= 2:
        # Check if second token is a suffix
        if tokens[1].upper() in SUFFIXES:
            suffix = tokens[1].upper()
            if len(tokens) >= 3:
                first_name = tokens[2].title()
        else:
            first_name = tokens[1].title()

    return ParsedOwner(
        is_organization=False,
        org_type=None,
        first_name=first_name,
        last_name=last_name,
        suffix=suffix,
        raw_name=name,
    )


def get_property_type(cat_code: str | None, descprop: str | None) -> str:
    """Determine property type from CAT code and DESCPROP."""
    if not cat_code:
        return "other"

    cat = cat_code.upper()

    if cat.startswith("R"):
        # R1 = single family, R2 = multi-family
        if cat == "R2":
            return "multi-family"
        return "residential"
    elif cat.startswith("C"):
        return "commercial"
    elif cat == "VL":
        return "land"

    return "other"


def get_dwelling_count_from_descprop(descprop: str | None) -> int:
    """Parse DESCPROP to estimate dwelling count.

    Patterns:
    - "& DWL" or "& DWL." → 1
    - "& 2 DWLS" → 2
    - "& MF" → 2 (conservative)
    """
    if not descprop:
        return 1

    text = descprop.upper()

    # Check for explicit count
    match = re.search(r'&\s*(\d+)\s*DWLS?', text)
    if match:
        return int(match.group(1))

    # Single dwelling
    if re.search(r'&\s*DWL[.\s:]?', text):
        return 1

    # Multi-family
    if "& MF" in text:
        return 2

    return 1


# =============================================================================
# Database Import
# =============================================================================

def clear_derived_tables(session: Session):
    """Clear tables that will be recreated."""
    print("  Clearing derived tables...")
    session.execute(delete(PropertyOwnership))
    session.execute(delete(Dwelling))
    session.execute(delete(Person))
    session.execute(delete(Organization))
    session.commit()
    print("  Cleared: property_ownerships, dwellings, people, organizations")


def import_all(session: Session, rows: list[VermontRow]):
    """Import all rows, creating parcels, dwellings, and owners."""

    # Group rows by SPAN
    span_groups: dict[str, list[VermontRow]] = defaultdict(list)
    for row in rows:
        span_groups[row.span].append(row)

    print(f"  {len(rows)} rows → {len(span_groups)} unique SPANs")

    # Track created entities
    parcels_created = 0
    parcels_updated = 0
    dwellings_created = 0
    people_created = 0
    orgs_created = 0
    ownerships_created = 0

    # Cache for deduplication
    person_cache: dict[str, Person] = {}  # "FIRST LAST" → Person
    org_cache: dict[str, Organization] = {}  # raw_name → Organization

    for span, unit_rows in span_groups.items():
        # Get or create parcel from first row
        first_row = unit_rows[0]

        parcel = session.execute(
            select(Parcel).where(Parcel.span == span)
        ).scalar_one_or_none()

        if parcel:
            # Update existing parcel
            parcel.address = first_row.address
            parcel.lat = first_row.lat
            parcel.lng = first_row.lng
            parcel.acres = first_row.acres
            parcel.assessed_land = first_row.assessed_land
            parcel.assessed_building = first_row.assessed_building
            parcel.assessed_total = first_row.assessed_total
            parcel.property_type = get_property_type(first_row.cat_code, first_row.descprop)
            parcels_updated += 1
        else:
            # Create new parcel
            parcel = Parcel(
                id=uuid4(),
                span=span,
                address=first_row.address,
                town=TOWN,
                lat=first_row.lat,
                lng=first_row.lng,
                acres=first_row.acres,
                assessed_land=first_row.assessed_land,
                assessed_building=first_row.assessed_building,
                assessed_total=first_row.assessed_total,
                property_type=get_property_type(first_row.cat_code, first_row.descprop),
            )
            session.add(parcel)
            parcels_created += 1

        session.flush()  # Get parcel.id

        # Create a dwelling for each row (each condo unit)
        for i, row in enumerate(unit_rows):
            # Determine if this is a condo unit
            is_condo = len(unit_rows) > 1
            unit_number = str(i + 1) if is_condo else None

            # Determine tax classification from homestead status
            if row.homestead_declared:
                tax_classification = "HOMESTEAD"
                use_type = "owner_occupied_primary"
            else:
                tax_classification = "NHS_RESIDENTIAL"
                use_type = "owner_occupied_secondary"

            # Create dwelling
            dwelling = Dwelling(
                id=uuid4(),
                parcel_id=parcel.id,
                unit_number=unit_number,
                assessed_value=row.assessed_total,
                tax_classification=tax_classification,
                use_type=use_type,
                homestead_filed=row.homestead_declared,
                occupant_name=row.owner_name,  # Owner as initial occupant
                data_source="grand_list",
            )
            session.add(dwelling)
            dwellings_created += 1

            session.flush()  # Get dwelling.id

            # Parse and create owner
            parsed = parse_owner_name(row.owner_name)
            if parsed:
                if parsed.is_organization:
                    # Get or create organization
                    org = org_cache.get(parsed.raw_name)
                    if not org:
                        # Map org_type string to enum
                        org_type_map = {
                            "llc": OrganizationType.LLC,
                            "trust": OrganizationType.TRUST,
                            "corporation": OrganizationType.CORPORATION,
                            "estate": OrganizationType.OTHER,
                        }
                        org = Organization(
                            id=uuid4(),
                            name=parsed.raw_name,
                            display_name=parsed.raw_name.title(),
                            org_type=org_type_map.get(parsed.org_type, OrganizationType.OTHER),
                            registered_state=row.mailing_state,
                            registered_address=row.mailing_address,
                        )
                        session.add(org)
                        org_cache[parsed.raw_name] = org
                        orgs_created += 1

                    session.flush()

                    # Create ownership link
                    ownership = PropertyOwnership(
                        id=uuid4(),
                        organization_id=org.id,
                        parcel_id=parcel.id,
                        dwelling_id=dwelling.id,
                        ownership_share=Decimal("1.0"),
                        ownership_type=OwnershipType.FEE_SIMPLE,
                        is_primary_owner=True,
                        as_listed_name=parsed.raw_name,
                        data_source="grand_list",
                    )
                    session.add(ownership)
                    ownerships_created += 1

                else:
                    # Get or create person
                    cache_key = f"{parsed.first_name or ''} {parsed.last_name or ''}".strip().upper()
                    person = person_cache.get(cache_key)

                    if not person:
                        # Determine residency from mailing state
                        is_warren_resident = (
                            row.mailing_state and
                            row.mailing_state.upper() == "VT" and
                            row.homestead_declared
                        )

                        # Build full mailing address
                        full_address = row.mailing_address or ""
                        if row.mailing_zip:
                            full_address = f"{full_address}, {row.mailing_zip}".strip(", ")

                        person = Person(
                            id=uuid4(),
                            first_name=parsed.first_name or "Unknown",
                            last_name=parsed.last_name or "Unknown",
                            suffix=parsed.suffix,
                            primary_address=full_address or None,
                            primary_town=row.mailing_city,
                            primary_state=row.mailing_state,
                            is_warren_resident=is_warren_resident,
                        )
                        session.add(person)
                        person_cache[cache_key] = person
                        people_created += 1

                    session.flush()

                    # Create ownership link
                    ownership = PropertyOwnership(
                        id=uuid4(),
                        person_id=person.id,
                        parcel_id=parcel.id,
                        dwelling_id=dwelling.id,
                        ownership_share=Decimal("1.0"),
                        ownership_type=OwnershipType.FEE_SIMPLE,
                        is_primary_owner=True,
                        as_listed_name=parsed.raw_name,
                        data_source="grand_list",
                    )
                    session.add(ownership)
                    ownerships_created += 1

        # Commit every 100 parcels
        if (parcels_created + parcels_updated) % 100 == 0:
            session.commit()
            print(f"    Processed {parcels_created + parcels_updated} parcels...")

    session.commit()

    print(f"\n  === Import Complete ===")
    print(f"  Parcels: {parcels_created} created, {parcels_updated} updated")
    print(f"  Dwellings: {dwellings_created} created")
    print(f"  People: {people_created} created")
    print(f"  Organizations: {orgs_created} created")
    print(f"  Ownerships: {ownerships_created} created")


# =============================================================================
# Statistics
# =============================================================================

def print_stats(session: Session):
    """Print current database statistics."""
    print("\n=== Database Statistics ===\n")

    # Table counts
    parcel_count = session.scalar(select(func.count(Parcel.id)))
    dwelling_count = session.scalar(select(func.count(Dwelling.id)))
    person_count = session.scalar(select(func.count(Person.id)))
    org_count = session.scalar(select(func.count(Organization.id)))
    ownership_count = session.scalar(select(func.count(PropertyOwnership.id)))

    print(f"Parcels: {parcel_count:,}")
    print(f"Dwellings: {dwelling_count:,}")
    print(f"People: {person_count:,}")
    print(f"Organizations: {org_count:,}")
    print(f"Property Ownerships: {ownership_count:,}")

    # Dwelling breakdown
    print("\n--- Dwelling Breakdown ---")
    result = session.execute(text("""
        SELECT
            tax_classification,
            COUNT(*) as count,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) as pct
        FROM dwellings
        GROUP BY tax_classification
        ORDER BY count DESC
    """)).fetchall()

    for row in result:
        print(f"  {row[0] or 'NULL'}: {row[1]:,} ({row[2]}%)")

    # Top condo complexes
    print("\n--- Top Condo Complexes (by dwelling count) ---")
    result = session.execute(text("""
        SELECT
            p.address,
            p.span,
            COUNT(d.id) as dwelling_count,
            SUM(CASE WHEN d.homestead_filed THEN 1 ELSE 0 END) as homestead_count
        FROM parcels p
        JOIN dwellings d ON d.parcel_id = p.id
        GROUP BY p.id, p.address, p.span
        HAVING COUNT(d.id) > 5
        ORDER BY COUNT(d.id) DESC
        LIMIT 10
    """)).fetchall()

    for row in result:
        print(f"  {row[0]}: {row[2]} dwellings ({row[3]} homestead)")

    # Organization ownership
    print("\n--- Organization Ownership ---")
    result = session.execute(text("""
        SELECT
            o.org_type,
            COUNT(DISTINCT o.id) as org_count,
            COUNT(po.id) as ownership_count
        FROM organizations o
        LEFT JOIN property_ownerships po ON po.organization_id = o.id
        GROUP BY o.org_type
        ORDER BY ownership_count DESC
    """)).fetchall()

    for row in result:
        print(f"  {row[0]}: {row[1]} orgs, {row[2]} ownerships")


def test_bridges(session: Session):
    """Test that The Bridges imported correctly."""
    print("\n=== Testing: The Bridges (C-219-0014) ===\n")

    result = session.execute(text("""
        SELECT
            d.unit_number,
            d.tax_classification,
            d.homestead_filed,
            d.assessed_value,
            COALESCE(p.first_name || ' ' || p.last_name, o.name) as owner
        FROM dwellings d
        JOIN parcels par ON d.parcel_id = par.id
        LEFT JOIN property_ownerships po ON po.dwelling_id = d.id
        LEFT JOIN people p ON po.person_id = p.id
        LEFT JOIN organizations o ON po.organization_id = o.id
        WHERE par.span = 'C-219-0014'
        ORDER BY d.unit_number
    """)).fetchall()

    if not result:
        print("  ERROR: No dwellings found for The Bridges!")
        return

    print(f"  Found {len(result)} dwellings")
    homestead_count = sum(1 for r in result if r[2])
    print(f"  Homestead filed: {homestead_count}")

    print("\n  Sample units:")
    for row in result[:5]:
        hs = "HS" if row[2] else "  "
        print(f"    Unit {row[0] or '-'}: {hs} {row[4] or 'Unknown':<30} ${row[3] or 0:>9,}")

    if len(result) > 5:
        print(f"    ... and {len(result) - 5} more")


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Unified Vermont Import")
    parser.add_argument("--fetch", action="store_true", help="Fetch from Vermont API")
    parser.add_argument("--import", dest="do_import", action="store_true", help="Import to database")
    parser.add_argument("--all", action="store_true", help="Fetch + Import")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--test", action="store_true", help="Test Bridges import")
    parser.add_argument("--clear", action="store_true", help="Clear derived tables first")
    args = parser.parse_args()

    if not any([args.fetch, args.do_import, args.all, args.stats, args.test]):
        parser.print_help()
        return

    # Create tables
    print("Creating tables if needed...")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        rows = []

        if args.fetch or args.all:
            print("\n=== Fetching from Vermont API ===")
            rows = list(fetch_all_rows())

        if args.do_import or args.all:
            if not rows:
                print("\n=== Fetching from Vermont API ===")
                rows = list(fetch_all_rows())

            if args.clear or args.all:
                clear_derived_tables(session)

            print("\n=== Importing to database ===")
            import_all(session, rows)

        if args.stats or args.all:
            print_stats(session)

        if args.test:
            test_bridges(session)


if __name__ == "__main__":
    main()
