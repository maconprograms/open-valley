"""Pydantic models for Bronze → Silver transformation.

These models encode the validation and normalization rules for transforming
raw data into clean, linked analytical data. The Field descriptions guide
the transformation logic.

Schema Engineering Philosophy:
- Intelligence lives in type hints and validators, not prose prompts
- Field(description=...) documents the expected transformation
- Validators auto-fix common issues and flag anomalies
"""

import re
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# State Code Normalization
# =============================================================================

# Map of common state name variations to 2-letter codes
STATE_CODES = {
    "VERMONT": "VT", "VT": "VT",
    "FLORIDA": "FL", "FL": "FL",
    "NEW YORK": "NY", "NY": "NY",
    "MASSACHUSETTS": "MA", "MA": "MA", "MASS": "MA",
    "CONNECTICUT": "CT", "CT": "CT", "CONN": "CT",
    "NEW HAMPSHIRE": "NH", "NH": "NH",
    "MAINE": "ME", "ME": "ME",
    "CALIFORNIA": "CA", "CA": "CA",
    "TEXAS": "TX", "TX": "TX",
    "NEW JERSEY": "NJ", "NJ": "NJ",
    "PENNSYLVANIA": "PA", "PA": "PA",
    "MARYLAND": "MD", "MD": "MD",
    "VIRGINIA": "VA", "VA": "VA",
    "NORTH CAROLINA": "NC", "NC": "NC",
    "SOUTH CAROLINA": "SC", "SC": "SC",
    "GEORGIA": "GA", "GA": "GA",
    "OHIO": "OH", "OH": "OH",
    "MICHIGAN": "MI", "MI": "MI",
    "ILLINOIS": "IL", "IL": "IL",
    "WASHINGTON": "WA", "WA": "WA",
    "OREGON": "OR", "OR": "OR",
    "COLORADO": "CO", "CO": "CO",
    "ARIZONA": "AZ", "AZ": "AZ",
    "NEVADA": "NV", "NV": "NV",
    "RHODE ISLAND": "RI", "RI": "RI",
    "DELAWARE": "DE", "DE": "DE",
    "DISTRICT OF COLUMBIA": "DC", "DC": "DC", "D.C.": "DC",
    "WEST VIRGINIA": "WV", "WV": "WV",
    "TENNESSEE": "TN", "TN": "TN",
    "KENTUCKY": "KY", "KY": "KY",
    "INDIANA": "IN", "IN": "IN",
    "WISCONSIN": "WI", "WI": "WI",
    "MINNESOTA": "MN", "MN": "MN",
    "IOWA": "IA", "IA": "IA",
    "MISSOURI": "MO", "MO": "MO",
    "ARKANSAS": "AR", "AR": "AR",
    "LOUISIANA": "LA", "LA": "LA",
    "MISSISSIPPI": "MS", "MS": "MS",
    "ALABAMA": "AL", "AL": "AL",
    "OKLAHOMA": "OK", "OK": "OK",
    "KANSAS": "KS", "KS": "KS",
    "NEBRASKA": "NE", "NE": "NE",
    "SOUTH DAKOTA": "SD", "SD": "SD",
    "NORTH DAKOTA": "ND", "ND": "ND",
    "MONTANA": "MT", "MT": "MT",
    "IDAHO": "ID", "ID": "ID",
    "WYOMING": "WY", "WY": "WY",
    "UTAH": "UT", "UT": "UT",
    "NEW MEXICO": "NM", "NM": "NM",
    "ALASKA": "AK", "AK": "AK",
    "HAWAII": "HI", "HI": "HI",
}


def normalize_state(raw_state: str | None) -> str | None:
    """Normalize state name/abbreviation to 2-letter code."""
    if not raw_state:
        return None
    clean = raw_state.strip().upper()
    return STATE_CODES.get(clean, clean[:2] if len(clean) == 2 else None)


# =============================================================================
# Intended Use Normalization
# =============================================================================

# Map raw intended_use values to normalized categories
INTENDED_USE_MAP = {
    "PRIMARY RESIDENCE": "primary",
    "SECONDARY RESIDENCE": "secondary",
    "VACATION HOME": "secondary",
    "VACATION": "secondary",
    "INVESTMENT": "investment",
    "RENTAL": "investment",
    "COMMERCIAL": "commercial",
    "AGRICULTURE": "agriculture",
    "FARM": "agriculture",
    "LAND": "land",
    "DEVELOPMENT": "development",
}


def normalize_intended_use(raw_use: str | None) -> str | None:
    """Normalize intended use to standard category."""
    if not raw_use:
        return None
    clean = raw_use.strip().upper()
    return INTENDED_USE_MAP.get(clean, "other")


# =============================================================================
# Bronze → Silver: Property Transfer Transformation
# =============================================================================


class PTTRBronzeInput(BaseModel):
    """Input model for raw PTTR data from bronze table."""

    id: UUID
    objectid: int
    span: str | None
    property_address: str | None
    town: str | None
    sale_price: int | None
    transfer_date: datetime | None
    transfer_type: str | None
    buyer_name: str | None
    buyer_state: str | None
    buyer_zip: str | None
    seller_name: str | None
    intended_use: str | None
    property_type_code: str | None
    lat: Decimal | None
    lng: Decimal | None


class PTTRSilverOutput(BaseModel):
    """Output model for validated property transfer (silver layer).

    Field descriptions encode the transformation rules.
    """

    bronze_id: UUID = Field(description="Reference to source bronze record")
    parcel_id: UUID | None = Field(
        default=None,
        description="Foreign key to parcels table, matched by SPAN"
    )

    span: str = Field(
        min_length=1,
        description="Vermont SPAN identifier, required for all transfers"
    )

    sale_price: int = Field(
        ge=0,
        description="Sale price in USD, must be non-negative"
    )

    transfer_date: datetime = Field(
        description="Date of property transfer"
    )

    transfer_type: str | None = Field(
        default=None,
        description="Type of transfer (Warranty Deed, Quitclaim, etc.)"
    )

    buyer_name: str | None = Field(default=None)
    buyer_state: str | None = Field(
        default=None,
        max_length=2,
        description="Normalized 2-letter state code"
    )
    is_out_of_state_buyer: bool = Field(
        default=False,
        description="True if buyer_state is not VT"
    )

    seller_name: str | None = Field(default=None)

    intended_use: str | None = Field(
        default=None,
        description="Normalized: primary, secondary, investment, commercial, agriculture, land, other"
    )
    is_primary_residence: bool | None = Field(
        default=None,
        description="True if intended_use is 'primary'"
    )
    is_secondary_residence: bool | None = Field(
        default=None,
        description="True if intended_use is 'secondary'"
    )

    validation_notes: str | None = Field(
        default=None,
        description="Notes about data quality issues or transformations applied"
    )

    @field_validator("buyer_state", mode="before")
    @classmethod
    def normalize_buyer_state(cls, v):
        """Auto-normalize state to 2-letter code."""
        return normalize_state(v)

    @field_validator("intended_use", mode="before")
    @classmethod
    def normalize_use(cls, v):
        """Auto-normalize intended use category."""
        return normalize_intended_use(v)

    @model_validator(mode="after")
    def derive_flags(self):
        """Derive boolean flags from normalized values."""
        if self.buyer_state:
            self.is_out_of_state_buyer = self.buyer_state != "VT"
        if self.intended_use:
            self.is_primary_residence = self.intended_use == "primary"
            self.is_secondary_residence = self.intended_use == "secondary"
        return self

    @classmethod
    def from_bronze(
        cls,
        bronze: PTTRBronzeInput,
        parcel_id: UUID | None = None,
    ) -> "PTTRSilverOutput | None":
        """Transform bronze record to silver.

        Returns None if record fails validation (missing required fields).
        """
        # Skip records missing required fields
        if not bronze.span or not bronze.sale_price or not bronze.transfer_date:
            return None

        notes = []

        # Check for suspicious data
        if bronze.sale_price == 0:
            notes.append("Zero sale price - may be interfamily transfer")
        if bronze.sale_price and bronze.sale_price > 10_000_000:
            notes.append(f"Unusually high sale price: ${bronze.sale_price:,}")

        return cls(
            bronze_id=bronze.id,
            parcel_id=parcel_id,
            span=bronze.span.strip(),
            sale_price=bronze.sale_price,
            transfer_date=bronze.transfer_date,
            transfer_type=bronze.transfer_type,
            buyer_name=bronze.buyer_name,
            buyer_state=bronze.buyer_state,
            seller_name=bronze.seller_name,
            intended_use=bronze.intended_use,
            validation_notes="; ".join(notes) if notes else None,
        )


# =============================================================================
# Bronze → Silver: STR Listing Transformation
# =============================================================================


class STRBronzeInput(BaseModel):
    """Input model for raw STR listing from bronze table."""

    id: UUID
    platform: str
    listing_id: str
    listing_url: str | None
    name: str | None
    property_type: str | None
    room_type: str | None
    address: str | None
    city: str | None
    state: str | None
    zip_code: str | None
    lat: Decimal | None
    lng: Decimal | None
    bedrooms: int | None
    bathrooms: Decimal | None
    max_guests: int | None
    price_per_night: Decimal | None
    currency: str | None
    host_name: str | None
    host_id: str | None
    is_superhost: bool | None
    total_reviews: int | None
    average_rating: Decimal | None
    first_review_date: datetime | None
    last_review_date: datetime | None
    scraped_at: datetime


# Property type normalization
STR_PROPERTY_TYPE_MAP = {
    "ENTIRE HOME": "entire_home",
    "ENTIRE HOUSE": "entire_home",
    "ENTIRE CABIN": "entire_home",
    "ENTIRE CONDO": "condo",
    "ENTIRE APARTMENT": "apartment",
    "PRIVATE ROOM": "private_room",
    "SHARED ROOM": "shared_room",
    "HOTEL": "hotel",
    "HOSTEL": "hostel",
}


def normalize_str_property_type(raw_type: str | None) -> str | None:
    """Normalize STR property type."""
    if not raw_type:
        return None
    clean = raw_type.strip().upper()
    # Check for partial matches
    for pattern, normalized in STR_PROPERTY_TYPE_MAP.items():
        if pattern in clean:
            return normalized
    return "other"


class STRSilverOutput(BaseModel):
    """Output model for validated STR listing (silver layer)."""

    bronze_id: UUID = Field(description="Reference to source bronze record")
    parcel_id: UUID | None = Field(
        default=None,
        description="Foreign key to parcels table, matched via spatial join or address"
    )
    match_method: Literal["spatial", "spatial_centroid", "address", "manual", None] = Field(
        default=None,
        description="Method used to match listing to parcel"
    )
    match_confidence: Decimal | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Confidence score for parcel match (0.0-1.0)"
    )

    platform: str = Field(description="airbnb or vrbo")
    listing_id: str = Field(description="Platform-specific listing ID")
    listing_url: str | None = Field(default=None)

    name: str | None = Field(default=None)
    property_type: str | None = Field(
        default=None,
        description="Normalized: entire_home, condo, apartment, private_room, shared_room, hotel, other"
    )

    lat: Decimal | None = Field(default=None)
    lng: Decimal | None = Field(default=None)

    bedrooms: int | None = Field(default=None, ge=0)
    max_guests: int | None = Field(default=None, ge=0)

    price_per_night_usd: int | None = Field(
        default=None,
        ge=0,
        description="Price in USD cents for precision"
    )

    total_reviews: int | None = Field(default=None, ge=0)
    average_rating: Decimal | None = Field(default=None, ge=0, le=5)
    is_active: bool = Field(
        default=True,
        description="False if listing appears to be inactive (no recent reviews)"
    )

    @field_validator("property_type", mode="before")
    @classmethod
    def normalize_property_type(cls, v):
        return normalize_str_property_type(v)

    @classmethod
    def from_bronze(
        cls,
        bronze: STRBronzeInput,
        parcel_id: UUID | None = None,
        match_method: str | None = None,
        match_confidence: float | None = None,
    ) -> "STRSilverOutput":
        """Transform bronze STR listing to silver."""
        # Determine if listing is active
        is_active = True
        if bronze.last_review_date:
            days_since_review = (datetime.utcnow() - bronze.last_review_date).days
            is_active = days_since_review < 365  # No reviews in a year = inactive

        # Convert price to USD (assume USD if currency not specified)
        price_usd = None
        if bronze.price_per_night:
            # Store as integer cents for precision
            price_usd = int(bronze.price_per_night * 100)

        return cls(
            bronze_id=bronze.id,
            parcel_id=parcel_id,
            match_method=match_method,
            match_confidence=Decimal(str(match_confidence)) if match_confidence else None,
            platform=bronze.platform.lower(),
            listing_id=bronze.listing_id,
            listing_url=bronze.listing_url,
            name=bronze.name,
            property_type=bronze.property_type,
            lat=bronze.lat,
            lng=bronze.lng,
            bedrooms=bronze.bedrooms,
            max_guests=bronze.max_guests,
            price_per_night_usd=price_usd,
            total_reviews=bronze.total_reviews,
            average_rating=bronze.average_rating,
            is_active=is_active,
        )


# =============================================================================
# Parcel Matching Utilities
# =============================================================================


class ParcelMatch(BaseModel):
    """Result of attempting to match a record to a parcel."""

    parcel_id: UUID | None = Field(default=None, description="Matched parcel ID or None")
    method: Literal["span", "spatial", "address", None] = Field(
        default=None,
        description="How the match was found"
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Match confidence"
    )
    notes: str | None = Field(default=None)


def match_by_span(span: str, span_to_parcel_id: dict[str, UUID]) -> ParcelMatch:
    """Match by SPAN identifier (highest confidence)."""
    # Normalize SPAN format
    clean_span = span.strip().upper().replace("-", "").replace(" ", "")
    parcel_id = span_to_parcel_id.get(clean_span)

    if parcel_id:
        return ParcelMatch(
            parcel_id=parcel_id,
            method="span",
            confidence=1.0,
        )
    return ParcelMatch(
        notes=f"No parcel found for SPAN: {span}"
    )


# =============================================================================
# Validation Statistics
# =============================================================================


class TransformationStats(BaseModel):
    """Statistics from a bronze → silver transformation run."""

    source: str = Field(description="Bronze table name")
    records_processed: int = 0
    records_valid: int = 0
    records_skipped: int = 0
    records_with_parcel_match: int = 0
    records_without_parcel_match: int = 0
    validation_errors: list[str] = Field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.records_processed == 0:
            return 0.0
        return self.records_valid / self.records_processed

    @property
    def parcel_match_rate(self) -> float:
        if self.records_valid == 0:
            return 0.0
        return self.records_with_parcel_match / self.records_valid


# =============================================================================
# Analysis Output Models (for agent tools)
# =============================================================================


class TransferTrend(BaseModel):
    """Property transfer trend for a time period."""

    period: str = Field(description="Year or year-month")
    total_transfers: int
    total_value: int
    avg_price: int
    out_of_state_count: int
    out_of_state_percent: float
    primary_residence_count: int
    secondary_residence_count: int

    @property
    def secondary_residence_percent(self) -> float:
        if self.total_transfers == 0:
            return 0.0
        return self.secondary_residence_count / self.total_transfers * 100


class STRSummary(BaseModel):
    """Summary of STR activity for a town or area."""

    total_listings: int
    active_listings: int
    total_bedrooms: int
    avg_price_per_night: int | None
    matched_to_parcel: int
    unmatched: int
    platforms: dict[str, int] = Field(default_factory=dict)
