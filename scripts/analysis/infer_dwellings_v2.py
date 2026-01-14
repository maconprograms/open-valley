"""Positive-signal-only dwelling inference.

CORE PRINCIPLE: Start with 0 dwellings. Add only where positive evidence exists.

Signal Hierarchy (Priority Order):
| Priority | Signal | Source | Confidence |
|----------|--------|--------|------------|
| 1 | DESCPROP "& DWL" | Grand List | 0.95 |
| 2 | homestead_filed = true | tax_status | 0.95 |
| 3 | housesite_value > 0 | Grand List HS_VALUE | 0.85 |
| 4 | STR listing matched | str_listings | 0.80 |

Do NOT create dwelling for:
- assessed_building > 0 alone (could be barn, garage)
- property_type = 'residential' alone (current bug)

Usage:
    uv run python scripts/analysis/infer_dwellings_v2.py              # Run inference
    uv run python scripts/analysis/infer_dwellings_v2.py --reset      # Clear and recreate
    uv run python scripts/analysis/infer_dwellings_v2.py --stats      # Show statistics
    uv run python scripts/analysis/infer_dwellings_v2.py --validate   # Validate calibration
"""

import argparse
import re
import sys
from decimal import Decimal
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
    DwellingType,
    DwellingUse,
    PropertyOwnership,
)


# =============================================================================
# DESCPROP Parsing
# =============================================================================

def parse_descprop_dwelling_count(descprop: str | None) -> int:
    """Parse DESCPROP field for dwelling count.

    Returns 0 if no dwelling signal found (key difference from v1).

    Patterns:
    - "& DWL" or "& DWL." or "& DWL:" → 1
    - "& 2 DWLS" → 2
    - "& MF" (multi-family) → 2 (conservative)
    - No pattern → 0 (no evidence of dwelling)
    """
    if not descprop:
        return 0

    text = descprop.upper()

    # Check for explicit count first: "& 2 DWLS", "& 3 DWLS"
    match = re.search(r'&\s*(\d+)\s*DWLS?', text)
    if match:
        return int(match.group(1))

    # Single dwelling: "& DWL", "& DWL.", "& DWL:"
    if re.search(r'&\s*DWL[.\s:]?', text):
        return 1

    # Multi-family indicator
    if "& MF" in text:
        return 2

    # No dwelling signal found
    return 0


def has_dwelling_signal(descprop: str | None) -> bool:
    """Check if DESCPROP contains any dwelling indicator."""
    return parse_descprop_dwelling_count(descprop) > 0


# =============================================================================
# Dwelling Classification
# =============================================================================

def classify_dwelling(
    parcel: Parcel,
    tax_status: TaxStatus | None,
    str_listing: STRListing | None,
    data_source: str,
) -> dict:
    """Determine dwelling attributes based on available data.

    Returns dict with:
    - dwelling_use: DwellingUse enum
    - dwelling_type: DwellingType enum
    - is_owner_occupied: bool | None
    - tax_classification: str (HOMESTEAD, NHS_RESIDENTIAL, NHS_NONRESIDENTIAL)
    """
    is_homestead = tax_status and tax_status.homestead_filed
    has_str = str_listing is not None

    if is_homestead:
        return {
            "dwelling_use": DwellingUse.FULL_TIME_RESIDENCE,
            "dwelling_type": DwellingType.MAIN_HOUSE,
            "is_owner_occupied": True,
            "tax_classification": "HOMESTEAD",
            "homestead_filed": True,
        }
    elif has_str:
        return {
            "dwelling_use": DwellingUse.SHORT_TERM_RENTAL,
            "dwelling_type": DwellingType.MAIN_HOUSE,
            "is_owner_occupied": False,
            "tax_classification": "NHS_RESIDENTIAL",
            "homestead_filed": False,
        }
    else:
        # Default: second home (most common in Warren)
        return {
            "dwelling_use": DwellingUse.SECOND_HOME,
            "dwelling_type": DwellingType.MAIN_HOUSE,
            "is_owner_occupied": None,
            "tax_classification": "NHS_RESIDENTIAL",
            "homestead_filed": False,
        }


# =============================================================================
# Positive-Signal Dwelling Inference
# =============================================================================

def infer_dwellings_positive_signal(session: Session, reset: bool = False) -> dict:
    """Create dwellings only where positive evidence exists.

    Signal priority:
    1. DESCPROP "& DWL" pattern → authoritative for count
    2. homestead_filed → at least 1 dwelling
    3. housesite_value > 0 → dwelling recognized by tax dept
    4. STR listing → someone renting it

    No signal → no dwelling created.
    """
    stats = {
        "parcels_total": 0,
        "parcels_with_dwellings": 0,
        "parcels_without_dwellings": 0,
        "dwellings_created": 0,
        "dwellings_homestead": 0,
        "dwellings_nhs_residential": 0,
        "by_source": {
            "descprop": 0,
            "homestead": 0,
            "housesite": 0,
            "str_listing": 0,
        },
        "skipped_no_signal": 0,
        "skipped_existing": 0,
    }

    if reset:
        print("Clearing existing dwellings...")
        # Clear property_ownerships that reference dwellings first
        session.execute(
            delete(PropertyOwnership).where(PropertyOwnership.dwelling_id.isnot(None))
        )
        session.execute(delete(Dwelling))
        session.commit()

    # Get all parcels
    parcels = session.execute(select(Parcel)).scalars().all()
    stats["parcels_total"] = len(parcels)

    print(f"Processing {len(parcels)} parcels with positive-signal logic...")
    print("  Signals: DESCPROP > homestead_filed > housesite_value > STR\n")

    for parcel in parcels:
        # Check if dwellings already exist
        if not reset:
            existing = session.scalar(
                select(func.count(Dwelling.id)).where(Dwelling.parcel_id == parcel.id)
            )
            if existing > 0:
                stats["skipped_existing"] += 1
                continue

        # Get related data
        tax_status = session.execute(
            select(TaxStatus).where(TaxStatus.parcel_id == parcel.id)
        ).scalar_one_or_none()

        str_listings = session.execute(
            select(STRListing).where(STRListing.parcel_id == parcel.id)
        ).scalars().all()

        # Apply positive-signal hierarchy
        dwellings_to_create = []

        # Signal 1: DESCPROP (authoritative for count)
        descprop_count = parse_descprop_dwelling_count(parcel.descprop)
        if descprop_count > 0:
            for i in range(descprop_count):
                # First unit may be homestead
                is_first = i == 0
                str_listing = str_listings[i] if i < len(str_listings) else None

                if is_first and tax_status and tax_status.homestead_filed:
                    attrs = classify_dwelling(parcel, tax_status, None, "descprop")
                else:
                    attrs = classify_dwelling(parcel, None, str_listing, "descprop")

                dwellings_to_create.append({
                    **attrs,
                    "data_source": "descprop",
                    "source_confidence": Decimal("0.95"),
                    "unit_number": None if descprop_count == 1 else f"Unit-{i+1}",
                    "str_listing": str_listing,
                    "notes": f"From DESCPROP: {parcel.descprop}",
                })
            stats["by_source"]["descprop"] += descprop_count

        # Signal 2: Homestead filed (at least 1 dwelling)
        elif tax_status and tax_status.homestead_filed:
            attrs = classify_dwelling(parcel, tax_status, None, "homestead")
            dwellings_to_create.append({
                **attrs,
                "data_source": "homestead",
                "source_confidence": Decimal("0.95"),
                "notes": "Homestead filed = dwelling exists",
            })
            stats["by_source"]["homestead"] += 1

        # Signal 3: Housesite value > 0
        elif tax_status and tax_status.housesite_value and tax_status.housesite_value > 0:
            str_listing = str_listings[0] if str_listings else None
            attrs = classify_dwelling(parcel, None, str_listing, "housesite")
            dwellings_to_create.append({
                **attrs,
                "data_source": "housesite",
                "source_confidence": Decimal("0.85"),
                "str_listing": str_listing,
                "notes": f"Housesite value: ${tax_status.housesite_value:,}",
            })
            stats["by_source"]["housesite"] += 1

        # Signal 4: STR listing exists
        elif str_listings:
            for str_listing in str_listings:
                attrs = classify_dwelling(parcel, None, str_listing, "str_listing")
                dwellings_to_create.append({
                    **attrs,
                    "data_source": "str_listing",
                    "source_confidence": Decimal("0.80"),
                    "str_listing": str_listing,
                    "notes": f"STR listing: {str_listing.platform} ({str_listing.bedrooms}BR)",
                })
            stats["by_source"]["str_listing"] += len(str_listings)

        # No positive signal → no dwelling
        else:
            stats["skipped_no_signal"] += 1
            stats["parcels_without_dwellings"] += 1
            continue

        # Create the dwellings
        stats["parcels_with_dwellings"] += 1

        for dw_data in dwellings_to_create:
            str_listing = dw_data.pop("str_listing", None)

            dwelling = Dwelling(
                parcel_id=parcel.id,
                unit_address=parcel.address,
                unit_number=dw_data.get("unit_number"),
                dwelling_type=dw_data.get("dwelling_type"),
                dwelling_use=dw_data.get("dwelling_use"),
                is_owner_occupied=dw_data.get("is_owner_occupied"),
                homestead_filed=dw_data.get("homestead_filed", False),
                str_listing_id=str_listing.id if str_listing else None,
                bedrooms=str_listing.bedrooms if str_listing else None,
                data_source=dw_data["data_source"],
                source_confidence=dw_data["source_confidence"],
                notes=dw_data.get("notes"),
            )
            session.add(dwelling)
            stats["dwellings_created"] += 1

            if dw_data.get("tax_classification") == "HOMESTEAD":
                stats["dwellings_homestead"] += 1
            else:
                stats["dwellings_nhs_residential"] += 1

    session.commit()
    return stats


# =============================================================================
# Statistics
# =============================================================================

def print_stats(session: Session):
    """Print dwelling statistics."""
    print("\n" + "=" * 60)
    print("DWELLING STATISTICS (Positive-Signal V2)")
    print("=" * 60)

    total_parcels = session.scalar(select(func.count(Parcel.id)))
    total_dwellings = session.scalar(select(func.count(Dwelling.id)))

    print(f"\nParcels in Grand List: {total_parcels:,}")
    print(f"Dwellings created:     {total_dwellings:,}")

    # Parcels with/without dwellings
    parcels_with = session.scalar(text("""
        SELECT COUNT(DISTINCT parcel_id) FROM dwellings
    """))
    print(f"\nParcels with dwellings:    {parcels_with:,} ({parcels_with/total_parcels*100:.1f}%)")
    print(f"Parcels without dwellings: {total_parcels - parcels_with:,} ({(total_parcels-parcels_with)/total_parcels*100:.1f}%)")

    # By data source
    print("\n--- By Data Source ---")
    result = session.execute(text("""
        SELECT data_source, COUNT(*) as count,
               AVG(source_confidence::numeric) as avg_confidence
        FROM dwellings
        GROUP BY data_source
        ORDER BY count DESC
    """)).fetchall()

    for row in result:
        source = row[0] or "unknown"
        count = row[1]
        conf = row[2] or 0
        pct = count / total_dwellings * 100 if total_dwellings else 0
        print(f"  {source}: {count:,} ({pct:.1f}%) [conf: {conf:.2f}]")

    # By tax classification
    print("\n--- By Classification ---")
    result = session.execute(text("""
        SELECT
            CASE
                WHEN homestead_filed THEN 'HOMESTEAD'
                ELSE 'NHS_RESIDENTIAL'
            END as classification,
            COUNT(*) as count
        FROM dwellings
        GROUP BY homestead_filed
        ORDER BY count DESC
    """)).fetchall()

    for row in result:
        pct = row[1] / total_dwellings * 100 if total_dwellings else 0
        print(f"  {row[0]}: {row[1]:,} ({pct:.1f}%)")

    # STR coverage
    str_dwellings = session.scalar(
        select(func.count(Dwelling.id)).where(Dwelling.str_listing_id.isnot(None))
    )
    total_str = session.scalar(select(func.count(STRListing.id)))
    print(f"\n--- STR Linkage ---")
    print(f"  STR listings:       {total_str:,}")
    print(f"  Dwellings with STR: {str_dwellings:,}")


def validate_calibration(session: Session):
    """Validate against calibration properties from CALIBRATION_PROPERTIES.md."""
    print("\n" + "=" * 60)
    print("CALIBRATION VALIDATION")
    print("=" * 60)

    # Test cases from docs/data-documentation/CALIBRATION_PROPERTIES.md
    calibration = [
        {
            "span": "690-219-11993",
            "address": "488 Woods Rd S",
            "expected_dwellings": 1,
            "expected_classification": "HOMESTEAD",
            "notes": "Phillips - owner occupied primary",
        },
        {
            "span": "690-219-13192",
            "address": "448 Woods Rd S",
            "expected_dwellings": 1,
            "expected_classification": "NHS_RESIDENTIAL",
            "notes": "Tremblay - second home",
        },
        {
            "span": "690-219-12656",
            "address": "200 Woods Rd S",
            "expected_dwellings": 1,  # ADU requires manual addition
            "expected_classification": "NHS_RESIDENTIAL",
            "notes": "Schulthess - second home (ADU not in Grand List)",
        },
        {
            "span": "690-219-12576",
            "address": "94 Woods Rd N",
            "expected_dwellings": 1,
            "expected_classification": "NHS_RESIDENTIAL",
            "notes": "Mad River LLC - STR",
        },
    ]

    all_pass = True

    for test in calibration:
        result = session.execute(text("""
            SELECT p.span, p.address, p.descprop,
                   COUNT(d.id) as dwellings,
                   STRING_AGG(d.data_source, ', ') as sources,
                   BOOL_OR(d.homestead_filed) as has_homestead
            FROM parcels p
            LEFT JOIN dwellings d ON d.parcel_id = p.id
            WHERE p.span = :span
            GROUP BY p.span, p.address, p.descprop
        """), {"span": test["span"]}).fetchone()

        if not result:
            print(f"\n[FAIL] {test['address']} - SPAN not found: {test['span']}")
            all_pass = False
            continue

        dwelling_count = result[3] or 0
        has_homestead = result[5] or False
        actual_class = "HOMESTEAD" if has_homestead else "NHS_RESIDENTIAL"

        count_ok = dwelling_count >= test["expected_dwellings"]
        class_ok = actual_class == test["expected_classification"]

        status = "[PASS]" if count_ok and class_ok else "[FAIL]"
        if status == "[FAIL]":
            all_pass = False

        print(f"\n{status} {test['address']}")
        print(f"  SPAN: {test['span']}")
        print(f"  DESCPROP: {result[2]}")
        print(f"  Dwellings: {dwelling_count} (expected: {test['expected_dwellings']})")
        print(f"  Classification: {actual_class} (expected: {test['expected_classification']})")
        print(f"  Sources: {result[4] or 'none'}")
        print(f"  Notes: {test['notes']}")

    print("\n" + "-" * 40)
    if all_pass:
        print("All calibration tests PASSED")
    else:
        print("Some calibration tests FAILED - review above")

    return all_pass


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Positive-signal dwelling inference (v2)"
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Clear and recreate all dwellings"
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Show statistics only"
    )
    parser.add_argument(
        "--validate", action="store_true",
        help="Validate against calibration properties"
    )
    args = parser.parse_args()

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        if args.stats:
            print_stats(session)
            return

        if args.validate:
            validate_calibration(session)
            return

        print("=" * 60)
        print("POSITIVE-SIGNAL DWELLING INFERENCE (V2)")
        print("=" * 60)
        print("\nCore Principle: Start with 0 dwellings.")
        print("Add only where positive evidence exists.\n")
        print("Signal Hierarchy:")
        print("  1. DESCPROP '& DWL' pattern (0.95)")
        print("  2. homestead_filed = true (0.95)")
        print("  3. housesite_value > 0 (0.85)")
        print("  4. STR listing exists (0.80)")
        print("  -- No signal → No dwelling\n")

        stats = infer_dwellings_positive_signal(session, reset=args.reset)

        print("\n--- Results ---")
        print(f"Parcels processed:        {stats['parcels_total']:,}")
        print(f"  With dwellings:         {stats['parcels_with_dwellings']:,}")
        print(f"  Without (no signal):    {stats['parcels_without_dwellings']:,}")
        print(f"Dwellings created:        {stats['dwellings_created']:,}")
        print(f"  HOMESTEAD:              {stats['dwellings_homestead']:,}")
        print(f"  NHS_RESIDENTIAL:        {stats['dwellings_nhs_residential']:,}")

        print(f"\n--- By Signal Source ---")
        for source, count in sorted(stats["by_source"].items(), key=lambda x: -x[1]):
            if count > 0:
                print(f"  {source}: {count:,}")

        if stats["skipped_no_signal"] > 0:
            print(f"\nSkipped (no signal):      {stats['skipped_no_signal']:,}")
        if stats["skipped_existing"] > 0:
            print(f"Skipped (existing):       {stats['skipped_existing']:,}")

        print_stats(session)


if __name__ == "__main__":
    main()
