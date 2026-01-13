"""Pydantic validation schemas for Open Valley data.

Schema Engineering Philosophy:
- Field descriptions ARE the prompts - they guide both validation and AI interpretation
- Validators enforce business rules from Vermont Act 73 and other authoritative sources
- These schemas serve as the contract between bronze (raw) and silver (validated) layers

References:
- Vermont Act 73 (2025): Property tax reform with three-class dwelling classification
- Vermont Homestead Declaration: https://tax.vermont.gov/property-owners/homestead-declaration
- RP-1354 Legislative Report: Dwelling classification guidance
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# =============================================================================
# ENUMS: Canonical value sets with descriptions
# =============================================================================


class TaxClassification(str, Enum):
    """Vermont Act 73 three-class property tax system.

    These classifications determine the property tax rate applied to each dwelling.
    A single parcel can have multiple dwellings with different classifications.
    """

    HOMESTEAD = "HOMESTEAD"
    """Owner's domicile for 6+ months per year. Taxed at education rate.

    Requirements:
    - Must be owner's principal dwelling
    - Owner must reside 6+ months per year
    - Must file annual homestead declaration
    - Cannot also be an STR operating 30+ days per year
    """

    NHS_RESIDENTIAL = "NHS_RESIDENTIAL"
    """Non-Homestead Residential: Second homes, STRs, vacant year-round dwellings.

    Applies to parcels with 1-4 dwelling units where:
    - Owner does not reside 6+ months/year, OR
    - Property is vacant but fit for year-round use, OR
    - Property is used as short-term rental (<30 days typical stay)

    Higher tax rate than HOMESTEAD.
    """

    NHS_NONRESIDENTIAL = "NHS_NONRESIDENTIAL"
    """Non-Homestead Non-Residential: Commercial, long-term rentals, 5+ units.

    Applies when:
    - Property has 5+ dwelling units (apartment building)
    - Dwelling is rented long-term (30+ day stays, 6+ months/year)
    - Property is used commercially
    - Property is seasonal/not fit for year-round use

    Highest tax rate.
    """


class DwellingUse(str, Enum):
    """How a dwelling is used - based on occupancy pattern.

    This answers: "Does someone live here full-time?"

    NOT about who owns it or whether there's an STR listing.
    Those are separate data points:
    - Owner info comes from PropertyOwnership → Person/Organization
    - STR listings are linked separately via str_listing_ids

    A homeowner who lists their house on Airbnb for 2 weeks over holidays
    still has use=FULL_TIME_RESIDENCE. The STR listing is separate data.
    """

    FULL_TIME_RESIDENCE = "full_time_residence"
    """Someone lives here year-round.

    Could be:
    - Owner-occupied (owner lives here as primary residence)
    - Tenant-occupied (long-term rental, tenant lives here)

    This dwelling provides housing to a community member.
    Use `is_owner_occupied` field to distinguish owner vs tenant.
    """

    SHORT_TERM_RENTAL = "short_term_rental"
    """Primarily used for short-term rentals (<30 day stays).

    No year-round resident lives here. Serves visitors/tourists.
    The dwelling is taken out of the housing supply.
    """

    SECOND_HOME = "second_home"
    """Vacation/second home - owner visits but doesn't live here.

    Owner may use it weekends, holidays, ski season, etc.
    Sits empty most of the year. Not owner's primary residence.
    May or may not have STR listing for when owner isn't visiting.
    """

    VACANT = "vacant"
    """Year-round habitable but sitting empty.

    No one lives here. Not rented. Just empty.
    Housing removed from supply entirely.
    """

    SEASONAL = "seasonal"
    """Not fit for year-round habitation.

    Camp, cabin without heat/insulation, summer cottage.
    Not a "dwelling" under Act 73 definition.
    """

    COMMERCIAL = "commercial"
    """Commercial use, 5+ unit building, or non-residential purpose."""

    UNKNOWN = "unknown"
    """Use cannot be determined from available data."""


class DwellingType(str, Enum):
    """Physical type of dwelling structure.

    This describes WHAT the structure is, not HOW it's used.
    A MAIN_HOUSE could be FULL_TIME_RESIDENCE or SECOND_HOME.
    An ADU could be rented long-term or used as an STR.

    Key distinction:
    - DwellingType = physical structure type (WHAT)
    - DwellingUse = occupancy pattern (HOW)
    """

    MAIN_HOUSE = "main_house"
    """Primary/main structure on the parcel.
    The "big house" - typically what Grand List knows about.
    """

    ADU = "adu"
    """Accessory Dwelling Unit.
    Secondary dwelling on same parcel as main house.
    Examples: apartment above garage, in-law suite, converted barn.
    Often invisible to Grand List - requires manual identification.
    """

    CONDO_UNIT = "condo_unit"
    """Unit in a condominium building.
    Multiple dwellings share one SPAN. Each has separate ownership.
    """

    APARTMENT = "apartment"
    """Unit in a multi-family rental building.
    Unlike condos, typically single owner for whole building.
    """

    DUPLEX_UNIT = "duplex_unit"
    """One unit in a two-family building (duplex)."""

    MOBILE_HOME = "mobile_home"
    """Mobile/manufactured home.
    May be on rented lot or owned land.
    """

    OTHER = "other"
    """Catch-all for unusual dwelling types."""


class OrganizationType(str, Enum):
    """Types of organizations that can own property or have members."""

    LLC = "llc"
    """Limited Liability Company. Cannot file homestead declarations.
    Example: "MAD RIVER LLC" owns 94 Woods Rd N (Brooklyn, NY)
    """

    TRUST = "trust"
    """Trust (revocable, irrevocable, etc.).
    Example: "WESTON STACEY B REVOCABLE TRUST"
    May have individual beneficiary who can claim homestead.
    """

    CORPORATION = "corporation"
    """Corporation (Inc., Corp.). Cannot file homestead declarations."""

    GOVERNMENT = "government"
    """Government body (town, state, federal).
    Example: Warren Planning Commission, Warren Selectboard
    """

    NONPROFIT = "nonprofit"
    """501(c)(3) or equivalent. Cannot file homestead declarations.
    Example: Mad River Valley Housing Coalition
    """

    ASSOCIATION = "association"
    """HOA, condo association, neighborhood group."""

    OTHER = "other"
    """Catch-all for unclassified entities."""


class OwnershipType(str, Enum):
    """Type of property ownership interest."""

    FEE_SIMPLE = "fee_simple"
    """Full ownership (most common)."""

    LIFE_ESTATE = "life_estate"
    """Right to use property for lifetime, then passes to remainderman."""

    TRUST_BENEFICIARY = "trust_beneficiary"
    """Beneficial interest through a trust."""

    JOINT_TENANCY = "joint_tenancy"
    """Joint ownership with right of survivorship."""

    TENANCY_IN_COMMON = "tenancy_in_common"
    """Joint ownership without right of survivorship."""


class TransactionType(str, Enum):
    """Type of property transfer."""

    SALE = "sale"
    """Arm's length sale for fair market value."""

    GIFT = "gift"
    """Transfer without consideration."""

    INHERITANCE = "inheritance"
    """Transfer upon death."""

    FORECLOSURE = "foreclosure"
    """Transfer due to mortgage default."""

    TAX_SALE = "tax_sale"
    """Transfer due to unpaid property taxes."""

    EXCHANGE = "exchange"
    """1031 exchange or similar."""

    OTHER = "other"
    """Catch-all for other transfer types."""


class IntendedUse(str, Enum):
    """Buyer's declared intended use on PTTR filing."""

    PRIMARY_RESIDENCE = "primary_residence"
    """Buyer intends to live here as primary home."""

    SECONDARY_RESIDENCE = "secondary_residence"
    """Buyer intends as vacation/second home."""

    INVESTMENT = "investment"
    """Buyer intends as rental/investment property."""

    COMMERCIAL = "commercial"
    """Buyer intends for commercial use."""

    UNKNOWN = "unknown"
    """Intent not declared or unclear."""


# =============================================================================
# CORE ENTITY SCHEMAS
# =============================================================================


class PersonBase(BaseModel):
    """A human individual in the Warren community.

    Person is the CENTRAL ENTITY connecting:
    - Property ownership (directly or through organizations)
    - Community participation (Front Porch Forum posts)
    - Government involvement (board/commission membership)
    - Dwelling residency (who lives where)

    Deduplication Strategy:
    1. Email match (highest confidence)
    2. Full name + road + town match
    3. Last name + mailing address match

    Examples:
    - Macon Phillips: property owner, FPF member, Planning Commission member
    - Fabio Schulthess: property owner (Swiss resident, not FPF member)
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    first_name: str = Field(
        min_length=1,
        max_length=100,
        description="First name as commonly used. May differ from legal name."
    )

    last_name: str = Field(
        min_length=1,
        max_length=100,
        description="Last name / family name."
    )

    full_name: str | None = Field(
        default=None,
        max_length=200,
        description="Full name as appears in official records (e.g., 'PHILLIPS III ROBERT M')."
    )

    suffix: str | None = Field(
        default=None,
        max_length=20,
        description="Name suffix: Jr, Sr, III, IV, etc.",
        examples=["Jr", "Sr", "III", "IV"]
    )

    email: str | None = Field(
        default=None,
        max_length=255,
        description="Primary email address. Best deduplication key when available."
    )

    phone: str | None = Field(
        default=None,
        max_length=20,
        description="Phone number in any format."
    )

    # Residency
    primary_address: str | None = Field(
        default=None,
        description="Where this person actually lives (may differ from property owned)."
    )

    primary_town: str | None = Field(
        default=None,
        max_length=50,
        description="Town of primary residence.",
        examples=["Warren", "Waitsfield", "Fayston"]
    )

    primary_state: str | None = Field(
        default=None,
        min_length=2,
        max_length=2,
        description="State of primary residence as 2-letter code. Use country code for international."
    )

    is_warren_resident: bool = Field(
        default=False,
        description="True if this person's primary residence is in Warren, VT."
    )

    # Data provenance
    data_sources: list[str] = Field(
        default_factory=list,
        description="Where we learned about this person: 'grand_list', 'fpf', 'pttr', 'manual'"
    )

    notes: str | None = Field(
        default=None,
        description="Free-form notes about this person."
    )

    @field_validator("primary_state")
    @classmethod
    def normalize_state(cls, v: str | None) -> str | None:
        """Normalize state to uppercase 2-letter code."""
        if v is None:
            return None
        return v.upper().strip()

    @model_validator(mode="after")
    def validate_warren_resident(self) -> "PersonBase":
        """Auto-set is_warren_resident based on primary location."""
        if self.primary_town and self.primary_state:
            self.is_warren_resident = (
                self.primary_town.lower() == "warren" and
                self.primary_state.upper() == "VT"
            )
        return self


class OrganizationBase(BaseModel):
    """An entity that can own property or have members.

    Organizations fall into two categories:

    1. PROPERTY-OWNING ENTITIES (extracted from Grand List owner names):
       - LLCs: "MAD RIVER LLC" → Cannot file homestead
       - Trusts: "WESTON STACEY B REVOCABLE TRUST" → May have individual beneficiary
       - Corporations: "SUGARBUSH RESORT INC"

    2. COMMUNITY/GOVERNMENT BODIES:
       - Government: Warren Planning Commission, Selectboard
       - Nonprofits: Mad River Valley Housing Coalition
       - Associations: HOAs, neighborhood groups

    Detection Patterns for Grand List Names:
    - LLC: r'\\bLLC\\b|\\bL\\.L\\.C\\b'
    - Trust: r'\\bTRUST\\b|\\bTRUSTEE\\b'
    - Corp: r'\\bINC\\b|\\bCORP\\b|\\bCORPORATION\\b'
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(
        min_length=1,
        max_length=255,
        description="Official name as appears in records (e.g., 'MAD RIVER LLC')."
    )

    display_name: str | None = Field(
        default=None,
        max_length=255,
        description="Friendly display name (e.g., 'Mad River LLC' instead of 'MAD RIVER LLC')."
    )

    org_type: OrganizationType = Field(
        description="Type of organization. Determines if homestead filing is possible."
    )

    registered_state: str | None = Field(
        default=None,
        min_length=2,
        max_length=2,
        description="State where registered (from mailing address). 2-letter code."
    )

    registered_address: str | None = Field(
        default=None,
        description="Official address of the organization."
    )

    notes: str | None = Field(
        default=None,
        description="Free-form notes."
    )

    @field_validator("registered_state")
    @classmethod
    def normalize_state(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return v.upper().strip()

    @property
    def can_file_homestead(self) -> bool:
        """True if this organization type can file a homestead declaration.

        In Vermont, only natural persons can claim homestead exemption.
        Trusts may allow this if the beneficiary is an individual.
        """
        return self.org_type == OrganizationType.TRUST


class DwellingBase(BaseModel):
    """A single habitable unit within a parcel.

    Vermont Act 73 Definition (Appendix 3):
    A "dwelling" is a building or part of a building that:
    1. Has separate means of ingress and egress
    2. Contains living facilities for sleeping, cooking, and sanitary needs
    3. Is fit for year-round habitation

    Key Distinctions:
    - Seasonal camps without insulation → NOT a dwelling
    - Apartment above garage with kitchen → IS a dwelling (often ADU)
    - Hotel rooms → NOT dwellings (commercial)
    - 5+ unit buildings → NHS_NONRESIDENTIAL classification

    Classification Rules:
    - HOMESTEAD: Owner lives here 6+ months/year
    - NHS_RESIDENTIAL: Second homes, STRs, vacant year-round
    - NHS_NONRESIDENTIAL: Long-term rentals, 5+ units, commercial
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    # Identification
    unit_number: str | None = Field(
        default=None,
        max_length=20,
        description="Unit identifier for multi-dwelling parcels (null for single-family).",
        examples=["A", "B", "Unit 1", "ADU-1"]
    )

    unit_address: str | None = Field(
        default=None,
        description="Full address including unit number."
    )

    dwelling_type: DwellingType | None = Field(
        default=None,
        description="Physical type of dwelling structure (WHAT it is, not HOW it's used)."
    )

    # Physical characteristics
    bedrooms: int | None = Field(
        default=None,
        ge=0,
        le=20,
        description="Number of bedrooms. 0 = studio."
    )

    bathrooms: Decimal | None = Field(
        default=None,
        ge=0,
        le=10,
        description="Number of bathrooms (half baths = 0.5)."
    )

    square_feet: int | None = Field(
        default=None,
        ge=0,
        description="Living area in square feet."
    )

    year_built: int | None = Field(
        default=None,
        ge=1700,
        le=2100,
        description="Year the dwelling was built."
    )

    # Act 73 Habitability Requirements
    has_separate_entrance: bool = Field(
        default=True,
        description="Has separate means of ingress/egress (Act 73 requirement)."
    )

    has_sleeping_facilities: bool = Field(
        default=True,
        description="Has facilities for sleeping (Act 73 requirement)."
    )

    has_cooking_facilities: bool = Field(
        default=True,
        description="Has facilities for cooking (Act 73 requirement)."
    )

    has_sanitary_facilities: bool = Field(
        default=True,
        description="Has sanitary facilities/bathroom (Act 73 requirement)."
    )

    is_year_round_habitable: bool = Field(
        default=True,
        description="Fit for year-round habitation (insulation, heating). If False, not a 'dwelling' under Act 73."
    )

    # === PRIMARY CLASSIFICATION: How is this dwelling used? ===
    use: DwellingUse | None = Field(
        default=None,
        description="How this dwelling is used (occupancy pattern). "
                    "Answers: 'Does someone live here full-time?' "
                    "NOT about ownership or STR listings - those are separate."
    )

    # For FULL_TIME_RESIDENCE - is it owner or tenant?
    is_owner_occupied: bool | None = Field(
        default=None,
        description="For FULL_TIME_RESIDENCE: True if owner lives here, False if tenant. "
                    "Determines HOMESTEAD vs NHS_NONRESIDENTIAL tax classification. "
                    "None for other use types or if unknown."
    )

    # === STR LISTING LINK (separate from use) ===
    str_listing_ids: list[str] = Field(
        default_factory=list,
        description="IDs of matched STR listings (Airbnb, VRBO) for this dwelling. "
                    "ANY dwelling can have STR listings - even FULL_TIME_RESIDENCE "
                    "(e.g., homeowner rents for 2 weeks over holidays). "
                    "Use=SHORT_TERM_RENTAL means STR is the PRIMARY use."
    )

    # Data provenance
    data_source: Literal["grand_list", "str_inference", "manual", "attestation"] = Field(
        default="grand_list",
        description="How this dwelling was identified."
    )

    source_confidence: Decimal | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Confidence in this dwelling data (0.0-1.0)."
    )

    notes: str | None = Field(
        default=None,
        description="Free-form notes, especially for manual corrections."
    )

    @property
    def is_habitable_dwelling(self) -> bool:
        """Check if this meets Act 73 dwelling definition.

        Must have ALL of:
        - Separate entrance
        - Sleeping facilities
        - Cooking facilities
        - Sanitary facilities
        - Year-round habitability
        """
        return all([
            self.has_separate_entrance,
            self.has_sleeping_facilities,
            self.has_cooking_facilities,
            self.has_sanitary_facilities,
            self.is_year_round_habitable,
        ])

    def get_tax_classification(self) -> TaxClassification | None:
        """Derive Act 73 tax classification from dwelling use + owner occupancy.

        Tax classification depends on:
        1. DwellingUse (occupancy pattern)
        2. For FULL_TIME_RESIDENCE: is_owner_occupied (owner vs tenant)
        """
        if not self.use:
            return None

        if self.use == DwellingUse.FULL_TIME_RESIDENCE:
            # Owner-occupied = HOMESTEAD, tenant-occupied = NHS_NONRESIDENTIAL
            if self.is_owner_occupied is True:
                return TaxClassification.HOMESTEAD
            elif self.is_owner_occupied is False:
                return TaxClassification.NHS_NONRESIDENTIAL  # LTR
            else:
                return None  # Unknown

        # All other uses map directly
        mapping = {
            DwellingUse.SHORT_TERM_RENTAL: TaxClassification.NHS_RESIDENTIAL,
            DwellingUse.SECOND_HOME: TaxClassification.NHS_RESIDENTIAL,
            DwellingUse.VACANT: TaxClassification.NHS_RESIDENTIAL,
            DwellingUse.COMMERCIAL: TaxClassification.NHS_NONRESIDENTIAL,
            DwellingUse.SEASONAL: None,  # Not a dwelling under Act 73
            DwellingUse.UNKNOWN: None,
        }
        return mapping.get(self.use)

    @property
    def has_str_listing(self) -> bool:
        """True if this dwelling has any matched STR listings."""
        return len(self.str_listing_ids) > 0

    @property
    def is_primary_str(self) -> bool:
        """True if SHORT_TERM_RENTAL is the primary use (not just occasional hosting)."""
        return self.use == DwellingUse.SHORT_TERM_RENTAL

    @property
    def adds_to_housing_supply(self) -> bool | None:
        """True if someone lives here year-round (adds to local housing supply)."""
        if not self.use:
            return None
        # Only FULL_TIME_RESIDENCE = someone lives here
        return self.use == DwellingUse.FULL_TIME_RESIDENCE

    @property
    def is_in_housing_supply(self) -> bool | None:
        """Alias for adds_to_housing_supply - does someone live here year-round?"""
        return self.adds_to_housing_supply


class PropertyOwnershipBase(BaseModel):
    """Records who owns what property.

    Ownership Complexity:
    - Individual: person_id set, organization_id null
    - Organizational: organization_id set, person_id null
    - Joint: Multiple records with ownership_share < 1.0

    Examples:
    - "PHILLIPS III ROBERT M & EMILY" → 2 records, each 0.5 share
    - "MAD RIVER LLC" → 1 record, organization owns 100%
    - "WESTON STACEY B REVOCABLE TRUST" → 1 organization record + linked person
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    # Must set exactly one of person_id or organization_id
    person_id: UUID | None = Field(
        default=None,
        description="If owned by individual, the person's ID."
    )

    organization_id: UUID | None = Field(
        default=None,
        description="If owned by organization (LLC, trust, etc.), the org's ID."
    )

    # Ownership details
    ownership_share: Decimal = Field(
        default=Decimal("1.0"),
        ge=0,
        le=1,
        description="Ownership percentage as decimal (0.5 = 50%)."
    )

    ownership_type: OwnershipType = Field(
        default=OwnershipType.FEE_SIMPLE,
        description="Type of ownership interest."
    )

    is_primary_owner: bool = Field(
        default=True,
        description="True if this is the primary/first-listed owner."
    )

    as_listed_name: str = Field(
        min_length=1,
        description="Owner name exactly as it appears in Grand List (preserve original text)."
    )

    # Dates
    acquired_date: date | None = Field(
        default=None,
        description="When ownership began (from PTTR if available)."
    )

    disposed_date: date | None = Field(
        default=None,
        description="When ownership ended (null if current owner)."
    )

    # Data provenance
    data_source: Literal["grand_list", "pttr", "manual"] = Field(
        default="grand_list",
        description="Where this ownership record came from."
    )

    @model_validator(mode="after")
    def validate_exactly_one_owner(self) -> "PropertyOwnershipBase":
        """Ensure exactly one of person_id or organization_id is set."""
        has_person = self.person_id is not None
        has_org = self.organization_id is not None

        if has_person == has_org:  # Both or neither
            raise ValueError(
                "Exactly one of person_id or organization_id must be set, not both or neither."
            )
        return self


class TransactionBase(BaseModel):
    """A property transfer event.

    Source: Vermont Property Transfer Tax Return (PTTR) filings.
    Each transfer requires a PTTR filing with buyer intent declaration.

    Key Fields for Residency Analysis:
    - buyer_state: Out-of-state buyers unlikely to be primary residents
    - intended_use: Buyer's declared intent (primary, secondary, investment)
    - sale_price: High prices often indicate investment properties

    Examples:
    - Primary residence purchase: VT buyer, "primary_residence" intent
    - Second home: NY buyer, "secondary_residence" intent
    - Investment: LLC buyer, "investment" intent
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    # Property identification
    span: str = Field(
        min_length=1,
        max_length=20,
        description="Vermont SPAN (School Property Account Number) linking to parcel."
    )

    # Transfer details
    sale_price: int = Field(
        ge=0,
        description="Sale price in dollars. 0 = gift or non-arm's length."
    )

    transfer_date: date = Field(
        description="Date of transfer (deed date)."
    )

    transfer_type: TransactionType = Field(
        default=TransactionType.SALE,
        description="Type of transfer."
    )

    # Buyer information
    buyer_name: str | None = Field(
        default=None,
        description="Buyer name(s) as listed on PTTR."
    )

    buyer_state: Annotated[str | None, Field(
        default=None,
        min_length=2,
        max_length=2,
        description="Buyer's state as 2-letter code. Critical for residency analysis."
    )]

    is_out_of_state_buyer: bool = Field(
        default=False,
        description="True if buyer_state is not 'VT'. Strong signal of non-primary residence."
    )

    # Seller information
    seller_name: str | None = Field(
        default=None,
        description="Seller name(s) as listed on PTTR."
    )

    # Intent (from PTTR filing)
    intended_use: IntendedUse = Field(
        default=IntendedUse.UNKNOWN,
        description="Buyer's declared intended use. Self-reported on PTTR filing."
    )

    is_primary_residence: bool | None = Field(
        default=None,
        description="True if intended_use is PRIMARY_RESIDENCE."
    )

    # Data provenance
    bronze_id: UUID | None = Field(
        default=None,
        description="ID of source record in bronze_pttr_transfers."
    )

    validation_notes: str | None = Field(
        default=None,
        description="Notes from validation process."
    )

    @field_validator("buyer_state")
    @classmethod
    def normalize_state(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return v.upper().strip()

    @model_validator(mode="after")
    def compute_derived_fields(self) -> "TransactionBase":
        """Compute derived fields from source data."""
        # Set is_out_of_state_buyer
        if self.buyer_state:
            self.is_out_of_state_buyer = self.buyer_state.upper() != "VT"

        # Set is_primary_residence from intended_use
        if self.intended_use:
            self.is_primary_residence = (
                self.intended_use == IntendedUse.PRIMARY_RESIDENCE
            )

        return self


class OrganizationMembershipBase(BaseModel):
    """Records membership/roles in organizations.

    Use Cases:
    1. LLC Members: "John Smith" is Managing Member of "Mad River LLC"
    2. Trust Relationships: "Stacey Weston" is Grantor/Trustee of "Weston Trust"
    3. Government Bodies: "Macon Phillips" is Commissioner on Planning Commission

    This enables:
    - Tracking who controls property-owning LLCs
    - Understanding community involvement
    - Connecting property ownership to individuals behind entities
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    person_id: UUID = Field(description="The person's ID.")
    organization_id: UUID = Field(description="The organization's ID.")

    role: str = Field(
        min_length=1,
        max_length=100,
        description="Role in organization: member, owner, trustee, commissioner, chair, etc."
    )

    title: str | None = Field(
        default=None,
        max_length=100,
        description="Official title if any (e.g., 'Managing Member', 'Chair')."
    )

    is_primary_contact: bool = Field(
        default=False,
        description="True if this person is the primary contact for the organization."
    )

    # Term
    start_date: date | None = Field(
        default=None,
        description="When membership/role began."
    )

    end_date: date | None = Field(
        default=None,
        description="When membership/role ended (null if current)."
    )

    is_active: bool = Field(
        default=True,
        description="True if this membership is currently active."
    )


class ChangeLogEntry(BaseModel):
    """Audit trail entry for data changes.

    All changes to core entities are tracked with:
    - What changed (table, record, field, values)
    - Who made the change (system or user)
    - Why (reason/source)
    - When verified (if applicable)

    This enables:
    - Tracking data quality improvements over time
    - Rolling back incorrect changes
    - Understanding data provenance
    - Accountability for manual corrections
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    # What changed
    table_name: str = Field(
        min_length=1,
        max_length=50,
        description="Table that was modified."
    )

    record_id: UUID = Field(description="ID of the modified record.")

    change_type: Literal["create", "update", "delete", "merge", "split"] = Field(
        description="Type of change."
    )

    field_name: str | None = Field(
        default=None,
        max_length=50,
        description="Which field changed (null for create/delete)."
    )

    old_value: str | None = Field(
        default=None,
        description="Previous value (JSON for complex types)."
    )

    new_value: str | None = Field(
        default=None,
        description="New value (JSON for complex types)."
    )

    # Who/why
    changed_by: str = Field(
        min_length=1,
        max_length=100,
        description="Who made the change: 'system:grand_list_import', 'user:macon', etc."
    )

    change_reason: str | None = Field(
        default=None,
        description="Why this change was made."
    )

    source_reference: str | None = Field(
        default=None,
        description="Link to source (SPAN, STR listing ID, etc.)."
    )

    # Verification
    verified_by: str | None = Field(
        default=None,
        max_length=100,
        description="Who verified this change."
    )

    verified_at: datetime | None = Field(
        default=None,
        description="When the change was verified."
    )

    verification_notes: str | None = Field(
        default=None,
        description="Notes from verification."
    )


# =============================================================================
# HELPER FUNCTIONS: Grand List Name Parsing
# =============================================================================


import re


def parse_owner_name(raw_name: str) -> tuple[list[dict], dict | None]:
    """Parse Grand List owner name into Person(s) and/or Organization.

    Examples:
    - "PHILLIPS III ROBERT M & EMILY" → [{"first": "Robert", "last": "Phillips", "suffix": "III"},
                                          {"first": "Emily", "last": "Phillips"}], None
    - "MAD RIVER LLC" → [], {"name": "MAD RIVER LLC", "type": "llc"}
    - "WESTON STACEY B REVOCABLE TRUST" → [{"first": "Stacey", "last": "Weston"}],
                                           {"name": "WESTON STACEY B REVOCABLE TRUST", "type": "trust"}

    Args:
        raw_name: Owner name exactly as appears in Grand List

    Returns:
        Tuple of (list of person dicts, organization dict or None)
    """
    # Detection patterns
    LLC_PATTERN = re.compile(r'\bLLC\b|\bL\.L\.C\b', re.IGNORECASE)
    TRUST_PATTERN = re.compile(r'\bTRUST\b|\bTRUSTEE\b', re.IGNORECASE)
    CORP_PATTERN = re.compile(r'\bINC\b|\bCORP\b|\bCORPORATION\b', re.IGNORECASE)

    people: list[dict] = []
    org: dict | None = None

    name = raw_name.strip()

    # Check for organization patterns
    if LLC_PATTERN.search(name):
        org = {"name": name, "type": OrganizationType.LLC.value}
        # LLCs typically don't have individual names to extract
        return people, org

    if CORP_PATTERN.search(name):
        org = {"name": name, "type": OrganizationType.CORPORATION.value}
        return people, org

    if TRUST_PATTERN.search(name):
        org = {"name": name, "type": OrganizationType.TRUST.value}
        # Try to extract the person's name from trust
        # "WESTON STACEY B REVOCABLE TRUST" → Stacey Weston
        trust_match = re.match(r'^([A-Z]+)\s+([A-Z]+)(?:\s+[A-Z]\.?)?\s+(?:REVOCABLE\s+)?TRUST', name)
        if trust_match:
            people.append({
                "last_name": trust_match.group(1).title(),
                "first_name": trust_match.group(2).title(),
            })
        return people, org

    # Parse individual names (possibly joint: "SMITH JOHN & JANE")
    # Common patterns:
    # - "LASTNAME FIRSTNAME"
    # - "LASTNAME FIRSTNAME & FIRSTNAME2"
    # - "LASTNAME FIRSTNAME M" (middle initial)
    # - "LASTNAME JR FIRSTNAME" (suffix before first name - Grand List quirk)

    # Split by "&" for joint ownership
    parts = [p.strip() for p in name.split("&")]

    for i, part in enumerate(parts):
        tokens = part.split()
        if not tokens:
            continue

        person: dict = {}

        if i == 0:
            # First person: "LASTNAME [SUFFIX] FIRSTNAME [MIDDLE]"
            # Check for suffix in position 2
            suffixes = {"JR", "SR", "II", "III", "IV", "V"}

            if len(tokens) >= 2:
                person["last_name"] = tokens[0].title()

                if len(tokens) >= 3 and tokens[1].upper() in suffixes:
                    person["suffix"] = tokens[1].upper()
                    person["first_name"] = tokens[2].title()
                else:
                    person["first_name"] = tokens[1].title()
        else:
            # Subsequent persons: just "FIRSTNAME" (shares last name with first)
            if len(tokens) >= 1:
                person["first_name"] = tokens[0].title()
                # Inherit last name from first person if available
                if people and "last_name" in people[0]:
                    person["last_name"] = people[0]["last_name"]

        if person.get("first_name"):
            people.append(person)

    return people, org


def parse_descprop_dwelling_count(descprop: str | None) -> int:
    """Parse Grand List DESCPROP field to get dwelling count.

    The DESCPROP field is MORE RELIABLE than CAT codes for dwelling count.

    Patterns:
    - "7.37 ACRES & DWL" → 1
    - "8.15 ACRES & DWL." → 1
    - "3.1 ACRES: & DWL" → 1
    - "5 ACRES & 2 DWLS" → 2
    - "10 ACRES & MF" → requires further analysis (multi-family)
    - "UNIT 3A" or "CONDO" → 1 (condo unit)

    Args:
        descprop: DESCPROP field value from Grand List

    Returns:
        Estimated number of dwellings (0 if cannot determine)
    """
    if not descprop:
        return 0

    text = descprop.upper()

    # Check for explicit count: "& 2 DWLS", "& 3 DWLS"
    multi_match = re.search(r'&\s*(\d+)\s*DWLS?', text)
    if multi_match:
        return int(multi_match.group(1))

    # Check for singular dwelling: "& DWL"
    if re.search(r'&\s*DWL[.\s:]?', text):
        return 1

    # Check for condo
    if "CONDO" in text or "UNIT" in text:
        return 1

    # Multi-family indicator (needs further analysis)
    if "& MF" in text:
        return 2  # Conservative estimate

    return 0  # Unknown


# =============================================================================
# STR REVIEW SCHEMAS
# Human-in-the-Loop review for STR-Dwelling linking
# =============================================================================


class STRReviewStatusEnum(str, Enum):
    """Review status for STR-dwelling linking."""
    UNREVIEWED = "unreviewed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    SKIPPED = "skipped"


class STRRejectionReason(str, Enum):
    """Reasons for rejecting an STR-dwelling link."""
    NOT_IN_WARREN = "not_in_warren"
    DUPLICATE = "duplicate"
    INVALID_LISTING = "invalid_listing"
    CANNOT_DETERMINE = "cannot_determine"
    OTHER = "other"


class STRReviewQueueItem(BaseModel):
    """STR listing in the review queue."""
    id: str = Field(description="UUID of the STR listing")
    platform: str = Field(description="Platform: airbnb, vrbo")
    listing_id: str = Field(description="Platform's listing ID")
    name: str | None = Field(default=None, description="Listing name/title")
    listing_url: str | None = Field(default=None, description="URL to listing")
    lat: float | None = Field(default=None, description="Latitude")
    lng: float | None = Field(default=None, description="Longitude")
    bedrooms: int | None = Field(default=None, description="Number of bedrooms")
    max_guests: int | None = Field(default=None, description="Maximum guests")
    price_per_night_usd: int | None = Field(default=None, description="Nightly rate in USD")
    total_reviews: int | None = Field(default=None, description="Total number of reviews")
    average_rating: float | None = Field(default=None, description="Average rating (0-5)")

    # Parcel match info
    parcel_id: str | None = Field(default=None, description="Matched parcel UUID")
    parcel_span: str | None = Field(default=None, description="Parcel SPAN ID")
    parcel_address: str | None = Field(default=None, description="Parcel address")
    match_method: str | None = Field(default=None, description="How match was made: spatial, address, manual")
    match_confidence: float | None = Field(default=None, ge=0, le=1, description="Match confidence 0-1")

    # Review state
    review_status: str = Field(default="unreviewed", description="Review status")
    dwelling_id: str | None = Field(default=None, description="Confirmed dwelling UUID")
    candidate_dwelling_count: int = Field(default=0, description="Number of dwellings on parcel")

    # Review metadata
    reviewed_by: str | None = Field(default=None)
    reviewed_at: str | None = Field(default=None)


class CandidateDwelling(BaseModel):
    """A candidate dwelling that an STR listing might belong to."""
    id: str = Field(description="UUID of the dwelling")
    unit_number: str | None = Field(default=None, description="Unit number if condo")
    use_type: str | None = Field(default=None, description="Use type from grand list")
    bedrooms: int | None = Field(default=None, description="Number of bedrooms")
    tax_classification: str | None = Field(default=None, description="HOMESTEAD, NHS_RESIDENTIAL, etc.")
    homestead_filed: bool = Field(default=False, description="Whether homestead was filed")
    existing_str_id: str | None = Field(default=None, description="Existing STR link if any")
    existing_str_name: str | None = Field(default=None, description="Name of existing linked STR")
    match_score: float = Field(default=0, ge=0, le=1, description="Computed match likelihood")


class STRReviewDetailResponse(BaseModel):
    """Detailed response for a single STR listing with candidates."""
    listing: STRReviewQueueItem
    candidates: list[CandidateDwelling] = Field(default_factory=list)
    parcel_geojson: dict | None = Field(default=None, description="GeoJSON geometry for the parcel")


class STRReviewQueueResponse(BaseModel):
    """Response for the review queue endpoint."""
    items: list[STRReviewQueueItem]
    total: int
    unreviewed_count: int
    confirmed_count: int
    rejected_count: int
    skipped_count: int


class STRReviewAction(BaseModel):
    """Request body for review action (confirm/reject/skip)."""
    action: Literal["confirm", "reject", "skip"] = Field(description="Action to take")
    dwelling_id: str | None = Field(
        default=None,
        description="UUID of dwelling to link (required if action=confirm)"
    )
    rejection_reason: str | None = Field(
        default=None,
        description="Reason for rejection (required if action=reject)"
    )
    notes: str | None = Field(default=None, description="Optional reviewer notes")

    @model_validator(mode="after")
    def validate_action_requirements(self) -> "STRReviewAction":
        if self.action == "confirm" and not self.dwelling_id:
            raise ValueError("dwelling_id is required when action is 'confirm'")
        if self.action == "reject" and not self.rejection_reason:
            raise ValueError("rejection_reason is required when action is 'reject'")
        return self


class STRReviewActionResponse(BaseModel):
    """Response after completing a review action."""
    success: bool
    listing_id: str
    action: str
    dwelling_id: str | None = None
    message: str


class STRReviewStats(BaseModel):
    """Statistics about review progress."""
    total_listings: int = Field(description="Total STR listings")
    matched_to_parcel: int = Field(description="Listings matched to a parcel")
    unreviewed: int
    confirmed: int
    rejected: int
    skipped: int
    completion_percent: float = Field(ge=0, le=100)
