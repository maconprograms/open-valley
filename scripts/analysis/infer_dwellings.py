"""Infer dwellings from Vermont Grand List parcel data.

DATA ARCHITECTURE PRINCIPLES:
1. Ground in PUBLIC DATA first (Grand List parcels = complete inventory)
2. Every parcel gets at least one dwelling (except pure land)
3. Multi-family parcels get multiple dwellings (estimate from value or default to 2)
4. Private data (STR) ENRICHES existing dwellings, doesn't create new ones

This ensures we account for "every square inch" of Warren before layering on
private data sources like AirROI STR listings.

Usage:
    uv run python scripts/infer_dwellings.py              # Create dwellings
    uv run python scripts/infer_dwellings.py --reset      # Clear and recreate all
    uv run python scripts/infer_dwellings.py --stats      # Show statistics
    uv run python scripts/infer_dwellings.py --coverage   # Show coverage analysis
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from src.database import engine
from src.models import (
    Base,
    Parcel,
    TaxStatus,
    STRListing,
    Dwelling,
)


# =============================================================================
# Dwelling Estimation Rules
# =============================================================================

def estimate_dwelling_count(parcel, tax_status) -> int:
    """Estimate number of dwelling units in a parcel.

    Rules:
    - land: 0 dwellings (undeveloped)
    - residential: 1 dwelling
    - other: 1 dwelling (condos, vacation homes, misc residential)
    - multi-family: estimate from assessed value or default to 2
    - commercial: 0 by default (could have apartments above, but rare)
    """
    prop_type = parcel.property_type or "unknown"

    if prop_type == "land":
        return 0

    if prop_type == "commercial":
        # Commercial properties generally don't have dwellings
        # Exception: mixed-use with apartments above (not in our data)
        return 0

    if prop_type == "multi-family":
        # Estimate units from assessed value
        # Rough heuristic: $300k per unit in Warren
        if parcel.assessed_total:
            estimated = max(2, parcel.assessed_total // 300_000)
            # Cap at reasonable maximum
            return min(estimated, 20)
        return 2  # Default for multi-family

    # residential, other, unknown -> 1 dwelling
    return 1


def classify_dwelling(parcel, tax_status, str_listing=None) -> tuple[str, str]:
    """Determine Act 73 tax classification and use type.

    Returns: (tax_classification, use_type)

    Act 73 Classifications:
    - HOMESTEAD: Owner's domicile for 6+ months/year
    - NHS_RESIDENTIAL: Second homes, STRs, vacant (1-4 units)
    - NHS_NONRESIDENTIAL: Commercial, long-term rentals, 5+ units
    """
    is_homestead = tax_status and tax_status.homestead_filed
    has_str = str_listing is not None

    if is_homestead:
        return ("HOMESTEAD", "owner_occupied_primary")
    elif has_str:
        return ("NHS_RESIDENTIAL", "short_term_rental")
    else:
        # Default: assume second home (most common in Warren)
        return ("NHS_RESIDENTIAL", "owner_occupied_secondary")


# =============================================================================
# Dwelling Creation
# =============================================================================

def infer_dwellings(session: Session, reset: bool = False) -> dict:
    """Create dwelling records from Grand List parcel data.

    Follows the principle: PUBLIC DATA FIRST
    1. Start with ALL parcels from Grand List
    2. Create dwellings based on parcel type
    3. Link STR listings to matching dwellings
    """
    stats = {
        "parcels_total": 0,
        "parcels_with_dwellings": 0,
        "parcels_without_dwellings": 0,
        "dwellings_created": 0,
        "dwellings_homestead": 0,
        "dwellings_nhs_residential": 0,
        "dwellings_nhs_nonresidential": 0,
        "dwellings_with_str": 0,
        "multi_family_units": 0,
        "skipped_existing": 0,
        "by_property_type": {},
    }

    if reset:
        print("Clearing existing dwellings...")
        session.execute(delete(Dwelling))
        session.commit()

    # Get ALL parcels - this is our complete inventory
    parcels = session.execute(select(Parcel)).scalars().all()
    stats["parcels_total"] = len(parcels)

    print(f"Processing {len(parcels)} parcels (complete Grand List inventory)...")

    for parcel in parcels:
        prop_type = parcel.property_type or "unknown"
        stats["by_property_type"][prop_type] = stats["by_property_type"].get(prop_type, 0)

        # Check if dwellings already exist for this parcel
        if not reset:
            existing_count = session.scalar(
                select(func.count(Dwelling.id)).where(Dwelling.parcel_id == parcel.id)
            )
            if existing_count > 0:
                stats["skipped_existing"] += 1
                continue

        # Get tax status
        tax_status = session.execute(
            select(TaxStatus).where(TaxStatus.parcel_id == parcel.id)
        ).scalar_one_or_none()

        # Estimate number of dwellings for this parcel
        dwelling_count = estimate_dwelling_count(parcel, tax_status)

        if dwelling_count == 0:
            stats["parcels_without_dwellings"] += 1
            continue

        stats["parcels_with_dwellings"] += 1
        stats["by_property_type"][prop_type] += dwelling_count

        # Get ALL STR listings for this parcel
        str_listings = session.execute(
            select(STRListing).where(STRListing.parcel_id == parcel.id)
        ).scalars().all()

        # Create dwellings
        if dwelling_count == 1:
            # Single dwelling - may or may not have STR
            str_listing = str_listings[0] if str_listings else None
            tax_class, use_type = classify_dwelling(parcel, tax_status, str_listing)

            dwelling = Dwelling(
                parcel_id=parcel.id,
                unit_address=parcel.address,
                bedrooms=str_listing.bedrooms if str_listing else None,
                year_built=parcel.year_built,
                tax_classification=tax_class,
                use_type=use_type,
                str_listing_id=str_listing.id if str_listing else None,
                data_source="grand_list_inference",
                notes=f"Inferred from {prop_type} parcel",
            )
            session.add(dwelling)
            stats["dwellings_created"] += 1

            if tax_class == "HOMESTEAD":
                stats["dwellings_homestead"] += 1
            elif tax_class == "NHS_RESIDENTIAL":
                stats["dwellings_nhs_residential"] += 1

            if str_listing:
                stats["dwellings_with_str"] += 1
        else:
            # Multi-unit property
            stats["multi_family_units"] += dwelling_count

            # First, create dwellings for each STR listing
            str_used = set()
            for i, str_listing in enumerate(str_listings):
                dwelling = Dwelling(
                    parcel_id=parcel.id,
                    unit_number=f"STR-{i+1}",
                    unit_address=parcel.address,
                    bedrooms=str_listing.bedrooms,
                    year_built=parcel.year_built,
                    tax_classification="NHS_RESIDENTIAL",
                    use_type="short_term_rental",
                    str_listing_id=str_listing.id,
                    data_source="grand_list_inference",
                    notes=f"Multi-family unit linked to STR",
                )
                session.add(dwelling)
                stats["dwellings_created"] += 1
                stats["dwellings_nhs_residential"] += 1
                stats["dwellings_with_str"] += 1
                str_used.add(str_listing.id)

            # Then create remaining units without STR
            remaining_units = dwelling_count - len(str_listings)

            # If homestead filed, first remaining unit is owner-occupied
            if tax_status and tax_status.homestead_filed and remaining_units > 0:
                dwelling = Dwelling(
                    parcel_id=parcel.id,
                    unit_number="Owner",
                    unit_address=parcel.address,
                    year_built=parcel.year_built,
                    tax_classification="HOMESTEAD",
                    use_type="owner_occupied_primary",
                    data_source="grand_list_inference",
                    notes="Owner unit in multi-family (homestead filed)",
                )
                session.add(dwelling)
                stats["dwellings_created"] += 1
                stats["dwellings_homestead"] += 1
                remaining_units -= 1

            # Rest are assumed secondary/rental
            for i in range(remaining_units):
                dwelling = Dwelling(
                    parcel_id=parcel.id,
                    unit_number=f"Unit-{i+1}",
                    unit_address=parcel.address,
                    year_built=parcel.year_built,
                    tax_classification="NHS_RESIDENTIAL",
                    use_type="owner_occupied_secondary",  # Could be rental - unknown
                    data_source="grand_list_inference",
                    notes=f"Multi-family unit {i+1} (use unknown)",
                )
                session.add(dwelling)
                stats["dwellings_created"] += 1
                stats["dwellings_nhs_residential"] += 1

    session.commit()
    return stats


# =============================================================================
# Statistics and Coverage
# =============================================================================

def print_stats(session: Session):
    """Print dwelling statistics."""
    print("\n" + "="*60)
    print("DWELLING STATISTICS")
    print("="*60)

    # Total counts
    total_parcels = session.scalar(select(func.count(Parcel.id)))
    total_dwellings = session.scalar(select(func.count(Dwelling.id)))

    print(f"\nParcels in Grand List: {total_parcels:,}")
    print(f"Dwellings inferred:    {total_dwellings:,}")

    # Parcels with/without dwellings
    parcels_with = session.scalar(text("""
        SELECT COUNT(DISTINCT parcel_id) FROM dwellings
    """))
    print(f"\nParcels with dwellings:    {parcels_with:,} ({parcels_with/total_parcels*100:.1f}%)")
    print(f"Parcels without dwellings: {total_parcels - parcels_with:,}")

    # By tax classification
    print("\n--- By Tax Classification (Act 73) ---")
    result = session.execute(text("""
        SELECT
            tax_classification,
            COUNT(*) as count,
            COUNT(str_listing_id) as with_str
        FROM dwellings
        GROUP BY tax_classification
        ORDER BY count DESC
    """)).fetchall()

    for row in result:
        pct = row[1] / total_dwellings * 100 if total_dwellings else 0
        print(f"  {row[0] or 'UNKNOWN'}: {row[1]:,} ({pct:.1f}%), {row[2]} STRs")

    # By use type
    print("\n--- By Use Type ---")
    result = session.execute(text("""
        SELECT use_type, COUNT(*) as count
        FROM dwellings
        GROUP BY use_type
        ORDER BY count DESC
    """)).fetchall()

    for row in result:
        pct = row[1] / total_dwellings * 100 if total_dwellings else 0
        print(f"  {row[0] or 'unknown'}: {row[1]:,} ({pct:.1f}%)")

    # Multi-unit properties
    print("\n--- Multi-Unit Properties ---")
    result = session.execute(text("""
        SELECT
            p.address,
            COUNT(d.id) as units,
            p.property_type,
            p.assessed_total
        FROM parcels p
        JOIN dwellings d ON d.parcel_id = p.id
        GROUP BY p.id, p.address, p.property_type, p.assessed_total
        HAVING COUNT(d.id) > 1
        ORDER BY COUNT(d.id) DESC
        LIMIT 10
    """)).fetchall()

    for row in result:
        val = f"${row[3]:,}" if row[3] else "N/A"
        print(f"  {row[0] or 'Unknown'}: {row[1]} units ({row[2]}, {val})")

    # STR coverage
    str_dwellings = session.scalar(
        select(func.count(Dwelling.id)).where(Dwelling.str_listing_id.isnot(None))
    )
    total_str = session.scalar(select(func.count(STRListing.id)))
    print(f"\n--- STR Linkage ---")
    print(f"  STR listings:           {total_str:,}")
    print(f"  Dwellings with STR:     {str_dwellings:,}")
    print(f"  STR coverage:           {str_dwellings/total_str*100:.1f}%" if total_str else "  No STR data")


def print_coverage(session: Session):
    """Print detailed coverage analysis."""
    print("\n" + "="*60)
    print("COVERAGE ANALYSIS: Are we accounting for every parcel?")
    print("="*60)

    # By property type
    print("\n--- Coverage by Property Type ---")
    result = session.execute(text("""
        SELECT
            p.property_type,
            COUNT(DISTINCT p.id) as parcels,
            COUNT(DISTINCT d.parcel_id) as parcels_with_dwellings,
            COUNT(d.id) as total_dwellings
        FROM parcels p
        LEFT JOIN dwellings d ON d.parcel_id = p.id
        GROUP BY p.property_type
        ORDER BY parcels DESC
    """)).fetchall()

    for row in result:
        prop_type = row[0] or "NULL"
        parcels = row[1]
        with_dw = row[2]
        total_dw = row[3]
        coverage = (with_dw / parcels * 100) if parcels else 0
        units_per = (total_dw / with_dw) if with_dw else 0

        print(f"\n  {prop_type}:")
        print(f"    Parcels: {parcels:,}")
        print(f"    With dwellings: {with_dw:,} ({coverage:.0f}%)")
        print(f"    Total dwellings: {total_dw:,}")
        if units_per > 1:
            print(f"    Avg units/parcel: {units_per:.1f}")

    # Missing parcels (should only be land/commercial)
    print("\n--- Parcels WITHOUT Dwellings (expected: land, commercial) ---")
    result = session.execute(text("""
        SELECT p.property_type, p.address, p.span, p.assessed_total
        FROM parcels p
        LEFT JOIN dwellings d ON d.parcel_id = p.id
        WHERE d.id IS NULL
        ORDER BY p.assessed_total DESC NULLS LAST
        LIMIT 15
    """)).fetchall()

    for row in result:
        val = f"${row[3]:,}" if row[3] else "N/A"
        print(f"  [{row[0]}] {row[1] or row[2]} - {val}")


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Infer dwellings from Grand List")
    parser.add_argument("--reset", action="store_true", help="Clear and recreate all dwellings")
    parser.add_argument("--stats", action="store_true", help="Show statistics only")
    parser.add_argument("--coverage", action="store_true", help="Show coverage analysis")
    args = parser.parse_args()

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        if args.stats:
            print_stats(session)
            return

        if args.coverage:
            print_coverage(session)
            return

        print("="*60)
        print("DWELLING INFERENCE FROM GRAND LIST")
        print("="*60)
        print("\nPrinciple: Ground in PUBLIC DATA first")
        print("  → Every parcel from Grand List = complete inventory")
        print("  → At least 1 dwelling per parcel (except land/commercial)")
        print("  → Multi-family = multiple dwelling units")
        print("  → STR data enriches, doesn't replace\n")

        stats = infer_dwellings(session, reset=args.reset)

        print(f"\n--- Results ---")
        print(f"Parcels processed:    {stats['parcels_total']:,}")
        print(f"  With dwellings:     {stats['parcels_with_dwellings']:,}")
        print(f"  Without (land/comm): {stats['parcels_without_dwellings']:,}")
        print(f"Dwellings created:    {stats['dwellings_created']:,}")
        print(f"  HOMESTEAD:          {stats['dwellings_homestead']:,}")
        print(f"  NHS_RESIDENTIAL:    {stats['dwellings_nhs_residential']:,}")
        print(f"  With STR:           {stats['dwellings_with_str']:,}")
        print(f"Multi-family units:   {stats['multi_family_units']:,}")

        if stats['skipped_existing'] > 0:
            print(f"Skipped (existing):   {stats['skipped_existing']:,}")

        print(f"\n--- By Property Type ---")
        for prop_type, count in sorted(stats['by_property_type'].items(), key=lambda x: -x[1]):
            print(f"  {prop_type}: {count:,} dwellings")

        print_stats(session)


if __name__ == "__main__":
    main()
