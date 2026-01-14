"""SQLAlchemy models for Warren community data.

Data Architecture Overview:
- Person is the CENTRAL ENTITY connecting property, community, and organizations
- Medallion Architecture: Bronze (raw) → Silver (validated) → Gold (aggregates)
- All changes tracked via ChangeLog audit trail

Key Concepts:
- DwellingType: WHAT the structure is (main_house, adu, condo_unit, etc.)
- DwellingUse: HOW it's used (full_time_residence, second_home, short_term_rental)
- is_owner_occupied: WHO lives there (owner vs tenant) - determines tax classification
- STR listings: SEPARATE DATA that can attach to any dwelling

Tax Classification (derived, not stored):
- HOMESTEAD: dwelling_use=FULL_TIME_RESIDENCE + is_owner_occupied=True
- NHS_RESIDENTIAL: second_home, short_term_rental, vacant (1-4 units)
- NHS_NONRESIDENTIAL: long-term rental, commercial, 5+ units

References:
- Vermont Act 73 (2025): Three-class dwelling tax system
- See docs/GLOSSARY.md for term definitions
- See src/schemas.py for Pydantic validation models
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from geoalchemy2 import Geometry
from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .schemas import (
    DwellingType,
    DwellingUse,
    OrganizationType,
    OwnershipType,
    TaxClassification,
)


class Parcel(Base):
    """A property parcel in Warren, VT."""

    __tablename__ = "parcels"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    span: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    address: Mapped[str | None] = mapped_column(Text)
    town: Mapped[str] = mapped_column(String(50), default="Warren")
    acres: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    assessed_land: Mapped[int | None] = mapped_column(Integer)
    assessed_building: Mapped[int | None] = mapped_column(Integer)
    assessed_total: Mapped[int | None] = mapped_column(Integer)
    property_type: Mapped[str | None] = mapped_column(String(20))  # residential, commercial, land
    descprop: Mapped[str | None] = mapped_column(
        Text,
        doc="DESCPROP from Vermont Grand List. Primary source for dwelling count. "
            "Patterns: '& DWL' (1), '& 2 DWLS' (2), '& MF' (multi-family)"
    )
    cat_code: Mapped[str | None] = mapped_column(
        String(10),
        doc="CAT code from Grand List. Less reliable than DESCPROP for dwelling count."
    )
    year_built: Mapped[int | None] = mapped_column(Integer)
    lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    geometry: Mapped[str | None] = mapped_column(Geometry("MULTIPOLYGON", srid=4326))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    property_ownerships: Mapped[list["PropertyOwnership"]] = relationship(
        "PropertyOwnership", back_populates="parcel"
    )
    tax_status: Mapped[list["TaxStatus"]] = relationship("TaxStatus", back_populates="parcel")
    transfers: Mapped[list["PropertyTransfer"]] = relationship(
        "PropertyTransfer", back_populates="parcel", foreign_keys="PropertyTransfer.parcel_id"
    )
    str_listings: Mapped[list["STRListing"]] = relationship(
        "STRListing", back_populates="parcel", foreign_keys="STRListing.parcel_id"
    )
    dwellings: Mapped[list["Dwelling"]] = relationship(
        "Dwelling", back_populates="parcel"
    )

    def __repr__(self) -> str:
        return f"<Parcel {self.span}: {self.address}>"


class TaxStatus(Base):
    """Tax status for a parcel in a given year."""

    __tablename__ = "tax_status"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    parcel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parcels.id"), nullable=False
    )
    tax_year: Mapped[int] = mapped_column(Integer, nullable=False)
    homestead_filed: Mapped[bool] = mapped_column(Boolean, default=False)
    housesite_value: Mapped[int | None] = mapped_column(Integer)
    education_tax: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    municipal_tax: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    # Relationships
    parcel: Mapped["Parcel"] = relationship("Parcel", back_populates="tax_status")

    def __repr__(self) -> str:
        return f"<TaxStatus {self.parcel_id} {self.tax_year}>"


# =============================================================================
# PERSON-CENTRIC MODELS
# =============================================================================


class Person(Base):
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

    __tablename__ = "people"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Identity
    first_name: Mapped[str] = mapped_column(
        String(100), nullable=False,
        doc="First name as commonly used"
    )
    last_name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
        doc="Last name / family name"
    )
    full_name: Mapped[str | None] = mapped_column(
        String(200),
        doc="Full name as appears in official records (e.g., 'PHILLIPS III ROBERT M')"
    )
    suffix: Mapped[str | None] = mapped_column(
        String(20),
        doc="Name suffix: Jr, Sr, III, etc."
    )

    # Contact
    email: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True,
        doc="Primary email address - best deduplication key when available"
    )
    phone: Mapped[str | None] = mapped_column(
        String(20),
        doc="Phone number"
    )

    # Residency (where this person actually lives)
    primary_address: Mapped[str | None] = mapped_column(
        Text,
        doc="Where this person actually lives (may differ from property owned)"
    )
    primary_town: Mapped[str | None] = mapped_column(
        String(50),
        doc="Town of primary residence"
    )
    primary_state: Mapped[str | None] = mapped_column(
        String(50),
        doc="State/province/country of primary residence"
    )
    is_warren_resident: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True,
        doc="True if this person's primary residence is in Warren, VT"
    )

    # FPF Linkage
    fpf_person_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fpf_people.id"),
        doc="Link to Front Porch Forum profile if matched"
    )

    # Data provenance
    data_sources: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        doc="Where we learned about this person: ['grand_list', 'fpf', 'pttr', 'manual']"
    )
    notes: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    property_ownerships: Mapped[list["PropertyOwnership"]] = relationship(
        "PropertyOwnership", back_populates="person"
    )
    organization_memberships: Mapped[list["OrganizationMembership"]] = relationship(
        "OrganizationMembership", back_populates="person"
    )
    fpf_person: Mapped["FPFPerson | None"] = relationship(
        "FPFPerson", foreign_keys=[fpf_person_id]
    )

    def __repr__(self) -> str:
        return f"<Person {self.first_name} {self.last_name}>"

    @property
    def display_name(self) -> str:
        """Full display name with suffix."""
        name = f"{self.first_name} {self.last_name}"
        if self.suffix:
            name += f" {self.suffix}"
        return name


class PropertyOwnership(Base):
    """Records who owns what property.

    Handles ownership complexity:
    - Individual ownership: person_id set, organization_id null
    - Organizational ownership: organization_id set, person_id null
    - Joint ownership: Multiple records with ownership_share < 1.0

    Examples:
    - "PHILLIPS III ROBERT M & EMILY" → 2 records, each 0.5 share
    - "MAD RIVER LLC" → 1 record, organization owns 100%
    - "WESTON STACEY B REVOCABLE TRUST" → 1 org record + linked person
    """

    __tablename__ = "property_ownerships"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Link to parcel
    parcel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parcels.id"), nullable=False, index=True
    )

    # Owner: exactly one of these must be set
    person_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("people.id"), index=True,
        doc="If owned by individual, the person's ID"
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True,
        doc="If owned by organization (LLC, trust, etc.), the org's ID"
    )

    # Link to dwelling (for condo units - multiple dwellings per parcel)
    dwelling_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dwellings.id"), index=True,
        doc="The specific dwelling unit owned (for condos with shared SPAN)"
    )

    # Ownership details
    ownership_share: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), default=Decimal("1.0"),
        doc="Ownership percentage as decimal (0.5 = 50%)"
    )
    ownership_type: Mapped[OwnershipType] = mapped_column(
        SQLEnum(OwnershipType), default=OwnershipType.FEE_SIMPLE,
        doc="Type of ownership interest: fee_simple, life_estate, trust_beneficiary, etc."
    )
    is_primary_owner: Mapped[bool] = mapped_column(
        Boolean, default=True,
        doc="True if this is the primary/first-listed owner"
    )

    # Preserve original Grand List text
    as_listed_name: Mapped[str] = mapped_column(
        Text, nullable=False,
        doc="Owner name exactly as it appears in Grand List"
    )

    # Dates
    acquired_date: Mapped[date | None] = mapped_column(
        Date,
        doc="When ownership began (from PTTR if available)"
    )
    disposed_date: Mapped[date | None] = mapped_column(
        Date,
        doc="When ownership ended (null if current owner)"
    )

    # Data provenance
    data_source: Mapped[str] = mapped_column(
        String(50), default="grand_list",
        doc="Where this ownership record came from: 'grand_list', 'pttr', 'manual'"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    parcel: Mapped["Parcel"] = relationship("Parcel", back_populates="property_ownerships")
    person: Mapped["Person | None"] = relationship("Person", back_populates="property_ownerships")
    organization: Mapped["Organization | None"] = relationship(
        "Organization", back_populates="property_ownerships"
    )
    dwelling: Mapped["Dwelling | None"] = relationship(
        "Dwelling", back_populates="property_ownerships"
    )

    def __repr__(self) -> str:
        owner = self.person.display_name if self.person else (
            self.organization.name if self.organization else "Unknown"
        )
        return f"<PropertyOwnership {owner} @ parcel {self.parcel_id}>"


class OrganizationMembership(Base):
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

    __tablename__ = "organization_memberships"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("people.id"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )

    # Role
    role: Mapped[str] = mapped_column(
        String(100), nullable=False,
        doc="Role in organization: member, owner, trustee, commissioner, chair, etc."
    )
    title: Mapped[str | None] = mapped_column(
        String(100),
        doc="Official title if any"
    )
    is_primary_contact: Mapped[bool] = mapped_column(
        Boolean, default=False,
        doc="True if this person is the primary contact for the organization"
    )

    # Term
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    person: Mapped["Person"] = relationship("Person", back_populates="organization_memberships")
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="memberships"
    )

    def __repr__(self) -> str:
        return f"<OrganizationMembership {self.person_id} -> {self.role} @ {self.organization_id}>"


class ChangeLog(Base):
    """Audit trail for all data changes.

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

    Triggered automatically via PostgreSQL triggers for key tables.
    """

    __tablename__ = "change_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # What changed
    table_name: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
        doc="Table that was modified"
    )
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True,
        doc="ID of the modified record"
    )
    change_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
        doc="Type of change: create, update, delete, merge, split"
    )
    field_name: Mapped[str | None] = mapped_column(
        String(50),
        doc="Which field changed (null for create/delete)"
    )
    old_value: Mapped[str | None] = mapped_column(
        Text,
        doc="Previous value (JSON for complex types)"
    )
    new_value: Mapped[str | None] = mapped_column(
        Text,
        doc="New value (JSON for complex types)"
    )

    # Who/why
    changed_by: Mapped[str] = mapped_column(
        String(100), nullable=False,
        doc="Who made the change: 'system:grand_list_import', 'user:macon', etc."
    )
    change_reason: Mapped[str | None] = mapped_column(
        Text,
        doc="Why this change was made"
    )
    source_reference: Mapped[str | None] = mapped_column(
        Text,
        doc="Link to source (SPAN, STR listing ID, etc.)"
    )

    # When
    changed_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    # Verification
    verified_by: Mapped[str | None] = mapped_column(String(100))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    verification_notes: Mapped[str | None] = mapped_column(Text)

    # Indexes
    __table_args__ = (
        Index('ix_change_log_table_record', 'table_name', 'record_id'),
    )

    def __repr__(self) -> str:
        return f"<ChangeLog {self.change_type} {self.table_name}.{self.field_name}>"


# Persistence models for conversations and artifacts

class Conversation(Base):
    """A chat conversation."""

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str | None] = mapped_column(String(100))
    title: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="conversation")


class Message(Base):
    """A message in a conversation."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant, tool
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
    artifacts: Mapped[list["Artifact"]] = relationship("Artifact", back_populates="message")


class Artifact(Base):
    """A shareable artifact (map, chart, table)."""

    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False
    )
    artifact_type: Mapped[str] = mapped_column(String(20), nullable=False)  # map, chart, table
    data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    message: Mapped["Message"] = relationship("Message", back_populates="artifacts")


class InviteCode(Base):
    """Invite codes for access."""

    __tablename__ = "invite_codes"

    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    created_by: Mapped[str | None] = mapped_column(String(100))
    used_by: Mapped[str | None] = mapped_column(String(100))
    used_at: Mapped[datetime | None] = mapped_column(DateTime)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)


# Front Porch Forum models


class FPFIssue(Base):
    """A daily Front Porch Forum email digest."""

    __tablename__ = "fpf_issues"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    issue_number: Mapped[int | None] = mapped_column(Integer, unique=True, index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    gmail_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    subject: Mapped[str | None] = mapped_column(Text)

    # Relationships
    posts: Mapped[list["FPFPost"]] = relationship("FPFPost", back_populates="issue")

    def __repr__(self) -> str:
        return f"<FPFIssue {self.issue_number}>"


class FPFPerson(Base):
    """A person who posts on Front Porch Forum."""

    __tablename__ = "fpf_people"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    road: Mapped[str | None] = mapped_column(Text)
    town: Mapped[str | None] = mapped_column(String(50), index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    posts: Mapped[list["FPFPost"]] = relationship("FPFPost", back_populates="person")

    def __repr__(self) -> str:
        return f"<FPFPerson {self.name}>"


class FPFPost(Base):
    """An individual post from an FPF digest."""

    __tablename__ = "fpf_posts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fpf_issues.id"), nullable=False
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fpf_people.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(50), index=True)
    is_reply: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Embedding columns for semantic search (3072 dims for text-embedding-3-large)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(3072), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    embedded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    issue: Mapped["FPFIssue"] = relationship("FPFIssue", back_populates="posts")
    person: Mapped["FPFPerson"] = relationship("FPFPerson", back_populates="posts")

    def __repr__(self) -> str:
        return f"<FPFPost {self.title[:30]}>"


class Organization(Base):
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

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Identity
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True,
        doc="Official name as appears in records (e.g., 'MAD RIVER LLC')"
    )
    display_name: Mapped[str | None] = mapped_column(
        String(255),
        doc="Friendly display name (e.g., 'Mad River LLC' instead of 'MAD RIVER LLC')"
    )
    org_type: Mapped[OrganizationType | None] = mapped_column(
        SQLEnum(OrganizationType),
        doc="Type of organization - determines if homestead filing is possible"
    )

    # Registration (for property-owning entities)
    registered_state: Mapped[str | None] = mapped_column(
        String(50),
        doc="State/country where registered (from mailing address)"
    )
    registered_address: Mapped[str | None] = mapped_column(
        Text,
        doc="Official address of the organization"
    )

    # For trusts: link to the grantor/beneficiary
    primary_person_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("people.id"),
        doc="For trusts: the person who created/benefits from the trust"
    )

    # Additional info
    description: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(Text)
    town: Mapped[str | None] = mapped_column(String(50), index=True)
    notes: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    property_ownerships: Mapped[list["PropertyOwnership"]] = relationship(
        "PropertyOwnership", back_populates="organization"
    )
    memberships: Mapped[list["OrganizationMembership"]] = relationship(
        "OrganizationMembership", back_populates="organization"
    )
    primary_person: Mapped["Person | None"] = relationship(
        "Person", foreign_keys=[primary_person_id]
    )

    def __repr__(self) -> str:
        return f"<Organization {self.name}>"

    @property
    def can_file_homestead(self) -> bool:
        """True if this organization type can file a homestead declaration.

        In Vermont, only natural persons can claim homestead exemption.
        Trusts may allow this if the beneficiary is an individual.
        """
        return self.org_type == OrganizationType.TRUST


# Note: pgvector 0.7.4 limits HNSW/IVFFlat indexes to 2000 dimensions.
# With text-embedding-3-large (3072 dims), we use sequential scan which is
# still fast for ~60k posts. For larger datasets, consider using the
# text-embedding-3-small model (1536 dims) with HNSW indexing.


# =============================================================================
# MEDALLION ARCHITECTURE: Bronze → Silver → Gold
# =============================================================================
#
# Bronze: Raw data exactly as received from external sources
# Silver: Cleaned, validated, and linked to our core entities
# Gold: Aggregated views for analytics (implemented as SQL views/materialized views)
#
# =============================================================================


# -----------------------------------------------------------------------------
# BRONZE LAYER: Property Transfer Tax Returns (PTTR)
# Source: Vermont Geodata Portal - FS_VCGI_OPENDATA_Cadastral_PTTR_point
# API: https://maps.vcgi.vermont.gov/arcgis/rest/services/EGC_services/OPENDATA_VCGI_PTTR_SP_NOCACHE_v1/FeatureServer/0
# -----------------------------------------------------------------------------


class BronzePTTRTransfer(Base):
    """Raw property transfer record from Vermont PTTR API.

    This is the raw data exactly as received from the API. Do not transform
    or validate here - that happens in the Silver layer.
    """

    __tablename__ = "bronze_pttr_transfers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # API identifiers
    objectid: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    globalid: Mapped[str | None] = mapped_column(String(50))

    # Property identification - RAW (may have formatting issues)
    span: Mapped[str | None] = mapped_column(String(20), index=True)  # Links to parcels
    property_address: Mapped[str | None] = mapped_column(Text)
    town: Mapped[str | None] = mapped_column(String(100))

    # Transfer details - RAW
    sale_price: Mapped[int | None] = mapped_column(Integer)
    transfer_date: Mapped[datetime | None] = mapped_column(DateTime)
    transfer_type: Mapped[str | None] = mapped_column(String(100))  # e.g. "Warranty Deed"

    # Buyer info - RAW
    buyer_name: Mapped[str | None] = mapped_column(Text)
    buyer_state: Mapped[str | None] = mapped_column(String(50))  # May need normalization
    buyer_zip: Mapped[str | None] = mapped_column(String(20))

    # Seller info - RAW
    seller_name: Mapped[str | None] = mapped_column(Text)

    # Usage/Intent - RAW (critical for residency analysis)
    intended_use: Mapped[str | None] = mapped_column(String(100))  # "Primary Residence", "Secondary Residence", etc.
    property_type_code: Mapped[str | None] = mapped_column(String(50))

    # Location - RAW from API
    lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))

    # Metadata
    raw_json: Mapped[str | None] = mapped_column(Text)  # Full API response for debugging
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    api_source: Mapped[str] = mapped_column(String(100), default="vcgi_pttr")

    def __repr__(self) -> str:
        return f"<BronzePTTR {self.span} ${self.sale_price} {self.transfer_date}>"


# -----------------------------------------------------------------------------
# BRONZE LAYER: Short-Term Rental Listings
# Source: Apify scrapers (Airbnb, VRBO)
# -----------------------------------------------------------------------------


class BronzeSTRListing(Base):
    """Raw short-term rental listing from Apify scrapers.

    Captures listings from Airbnb, VRBO, and other platforms exactly as scraped.
    """

    __tablename__ = "bronze_str_listings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Platform identification
    platform: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # airbnb, vrbo
    listing_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    listing_url: Mapped[str | None] = mapped_column(Text)

    # Property details - RAW
    name: Mapped[str | None] = mapped_column(Text)
    property_type: Mapped[str | None] = mapped_column(String(100))  # "Entire home", "Private room", etc.
    room_type: Mapped[str | None] = mapped_column(String(100))

    # Location - RAW (may be approximate/jittered for privacy)
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(50))
    zip_code: Mapped[str | None] = mapped_column(String(20))
    lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))

    # Capacity/Size
    bedrooms: Mapped[int | None] = mapped_column(Integer)
    bathrooms: Mapped[Decimal | None] = mapped_column(Numeric(3, 1))
    max_guests: Mapped[int | None] = mapped_column(Integer)

    # Pricing - RAW
    price_per_night: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    currency: Mapped[str | None] = mapped_column(String(10))

    # Host info
    host_name: Mapped[str | None] = mapped_column(Text)
    host_id: Mapped[str | None] = mapped_column(String(100))
    is_superhost: Mapped[bool | None] = mapped_column(Boolean)

    # Availability/Activity
    total_reviews: Mapped[int | None] = mapped_column(Integer)
    average_rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    first_review_date: Mapped[datetime | None] = mapped_column(DateTime)
    last_review_date: Mapped[datetime | None] = mapped_column(DateTime)

    # Metadata
    raw_json: Mapped[str | None] = mapped_column(Text)  # Full scraper output
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    scraper_run_id: Mapped[str | None] = mapped_column(String(100))
    api_source: Mapped[str | None] = mapped_column(String(50))  # "airroi", "apify_airbnb", etc.

    # Composite unique constraint
    __table_args__ = (
        Index('ix_bronze_str_platform_listing', 'platform', 'listing_id', unique=True),
    )

    def __repr__(self) -> str:
        return f"<BronzeSTR {self.platform}:{self.listing_id}>"


# -----------------------------------------------------------------------------
# SILVER LAYER: Validated Property Transfers
# Cleaned, normalized, and linked to parcels
# -----------------------------------------------------------------------------


class PropertyTransfer(Base):
    """Validated property transfer linked to parcel.

    Silver layer: Cleaned data with foreign key to parcels table.
    Buyer state normalized to 2-letter codes, dates validated, etc.
    """

    __tablename__ = "property_transfers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Link to bronze source
    bronze_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bronze_pttr_transfers.id"), nullable=False
    )

    # Link to parcel (may be null if SPAN doesn't match)
    parcel_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parcels.id"), nullable=True, index=True
    )

    # Validated identifiers
    span: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Validated transfer details
    sale_price: Mapped[int] = mapped_column(Integer, nullable=False)
    transfer_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    transfer_type: Mapped[str | None] = mapped_column(String(100))

    # Normalized buyer info
    buyer_name: Mapped[str | None] = mapped_column(Text)
    buyer_state: Mapped[str | None] = mapped_column(String(2))  # Normalized to 2-letter code
    is_out_of_state_buyer: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Seller info
    seller_name: Mapped[str | None] = mapped_column(Text)

    # Normalized usage classification
    intended_use: Mapped[str | None] = mapped_column(String(50))  # Normalized categories
    is_primary_residence: Mapped[bool | None] = mapped_column(Boolean)
    is_secondary_residence: Mapped[bool | None] = mapped_column(Boolean)

    # Validation metadata
    validated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    validation_notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    parcel: Mapped["Parcel"] = relationship("Parcel", foreign_keys=[parcel_id])
    bronze_record: Mapped["BronzePTTRTransfer"] = relationship("BronzePTTRTransfer")

    def __repr__(self) -> str:
        return f"<PropertyTransfer {self.span} ${self.sale_price} {self.transfer_date}>"


# -----------------------------------------------------------------------------
# SILVER LAYER: Validated STR Listings (matched to parcels)
# -----------------------------------------------------------------------------


class STRListing(Base):
    """Validated STR listing matched to parcel via spatial join or address.

    Silver layer: Cleaned, geocoded, and linked to our parcel layer.
    """

    __tablename__ = "str_listings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Link to bronze source
    bronze_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bronze_str_listings.id"), nullable=False
    )

    # Link to parcel (may be null if no match)
    parcel_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parcels.id"), nullable=True, index=True
    )
    match_method: Mapped[str | None] = mapped_column(String(50))  # spatial, spatial_centroid, address, manual
    match_confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))  # 0.00 to 1.00

    # Platform info
    platform: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    listing_id: Mapped[str] = mapped_column(String(100), nullable=False)
    listing_url: Mapped[str | None] = mapped_column(Text)

    # Property details (validated)
    name: Mapped[str | None] = mapped_column(Text)
    property_type: Mapped[str | None] = mapped_column(String(50))  # Normalized

    # Validated location
    lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))

    # Capacity
    bedrooms: Mapped[int | None] = mapped_column(Integer)
    max_guests: Mapped[int | None] = mapped_column(Integer)

    # Pricing (normalized to USD)
    price_per_night_usd: Mapped[int | None] = mapped_column(Integer)

    # Activity metrics
    total_reviews: Mapped[int | None] = mapped_column(Integer)
    average_rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Validation metadata
    validated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    parcel: Mapped["Parcel"] = relationship("Parcel", foreign_keys=[parcel_id])
    bronze_record: Mapped["BronzeSTRListing"] = relationship("BronzeSTRListing")

    def __repr__(self) -> str:
        return f"<STRListing {self.platform}:{self.listing_id}>"


# -----------------------------------------------------------------------------
# STR REVIEW: Human-in-the-Loop Review Status
# Tracks the review state for linking STR listings to dwellings
# -----------------------------------------------------------------------------


class STRReviewStatus(Base):
    """Review status for STR-dwelling linking.

    Tracks the human review process for confirming, rejecting, or skipping
    STR → Dwelling associations. Kept separate from STRListing to maintain
    clean Silver layer data.

    Workflow:
    1. STRListing is spatially matched to a Parcel
    2. Parcel may have multiple Dwellings (condos, ADUs)
    3. Human reviewer confirms which Dwelling the STR belongs to
    4. On confirm: dwelling.str_listing_id is set as canonical link
    """

    __tablename__ = "str_review_status"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    str_listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("str_listings.id"),
        unique=True, nullable=False, index=True,
        doc="The STR listing being reviewed"
    )

    # Review state
    status: Mapped[str] = mapped_column(
        String(20), default="unreviewed", index=True,
        doc="Review status: unreviewed, confirmed, rejected, skipped"
    )

    # Confirmed link (set when status=confirmed)
    dwelling_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dwellings.id"),
        doc="Dwelling confirmed by reviewer (null until confirmed)"
    )

    # Rejection info (set when status=rejected)
    rejection_reason: Mapped[str | None] = mapped_column(
        String(100),
        doc="Reason for rejection: not_in_warren, duplicate, invalid, cannot_determine, other"
    )

    # Audit trail
    notes: Mapped[str | None] = mapped_column(
        Text,
        doc="Reviewer notes or additional context"
    )
    reviewed_by: Mapped[str | None] = mapped_column(
        String(100),
        doc="Username or identifier of reviewer"
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        doc="When the review was completed"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    str_listing: Mapped["STRListing"] = relationship("STRListing")
    dwelling: Mapped["Dwelling | None"] = relationship("Dwelling")

    def __repr__(self) -> str:
        return f"<STRReviewStatus {self.str_listing_id} status={self.status}>"


# -----------------------------------------------------------------------------
# DWELLING LAYER: Act 73 Multi-Dwelling Support
# A parcel can contain multiple dwelling units, each classified independently
# -----------------------------------------------------------------------------


class Dwelling(Base):
    """A single habitable unit within a parcel.

    Vermont Act 73 (2025) Definition:
    A "dwelling" is a building or part of building that:
    1. Has separate means of ingress/egress
    2. Contains living facilities for sleeping, cooking, and sanitary needs
    3. Is fit for year-round habitation

    Key Model Concepts:

    1. DwellingType (WHAT it is physically):
       - MAIN_HOUSE: Primary structure on parcel
       - ADU: Accessory Dwelling Unit (apt above garage, in-law suite)
       - CONDO_UNIT: Unit in condo building (shared SPAN)
       - APARTMENT: Unit in multi-family rental building

    2. DwellingUse (HOW it's used - occupancy pattern):
       - FULL_TIME_RESIDENCE: Someone lives here year-round
       - SECOND_HOME: Owner visits occasionally, not rented
       - SHORT_TERM_RENTAL: Primarily STR, no year-round resident
       - VACANT: Empty, not rented

    3. is_owner_occupied (WHO lives here):
       - True: Owner lives here (HOMESTEAD eligible)
       - False: Tenant lives here (long-term rental → NHS_NONRESIDENTIAL)
       - None: Unknown or not applicable

    4. STR Listings (SEPARATE DATA):
       - str_listing_id links to matched STR listing
       - ANY dwelling can have STR listing, even FULL_TIME_RESIDENCE
       - dwelling_use=SHORT_TERM_RENTAL means STR is PRIMARY use

    Tax Classification (DERIVED, not stored):
    - HOMESTEAD: dwelling_use=FULL_TIME_RESIDENCE + is_owner_occupied=True
    - NHS_RESIDENTIAL: second_home, short_term_rental, vacant (1-4 units)
    - NHS_NONRESIDENTIAL: is_owner_occupied=False (LTR), commercial, 5+ units

    Examples from calibration properties (see CALIBRATION_PROPERTIES.md):
    - Phillips 488 Woods Rd: MAIN_HOUSE, FULL_TIME_RESIDENCE, is_owner_occupied=True → HOMESTEAD
    - Tremblay 448 Woods Rd: MAIN_HOUSE, SECOND_HOME → NHS_RESIDENTIAL
    - Schulthess 200 Woods Rd: MAIN_HOUSE (SECOND_HOME) + ADU (FULL_TIME_RESIDENCE, is_owner_occupied=False)
    - Mad River LLC 94 Woods Rd: MAIN_HOUSE, SHORT_TERM_RENTAL → NHS_RESIDENTIAL
    """

    __tablename__ = "dwellings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ==========================================================================
    # PARCEL RELATIONSHIP
    # ==========================================================================
    parcel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parcels.id"), nullable=False, index=True,
        doc="Parent parcel (1 parcel → N dwellings)"
    )

    # ==========================================================================
    # IDENTIFICATION (for multi-dwelling parcels)
    # ==========================================================================
    unit_number: Mapped[str | None] = mapped_column(
        String(20),
        doc="Unit identifier: 'A', 'B', 'Unit 1', 'ADU-1'. Null for single-family."
    )
    unit_address: Mapped[str | None] = mapped_column(
        Text,
        doc="Full address including unit, if different from parcel address"
    )

    # ==========================================================================
    # DWELLING TYPE (WHAT is it physically?)
    # ==========================================================================
    dwelling_type: Mapped[DwellingType | None] = mapped_column(
        SQLEnum(DwellingType), index=True,
        doc="Physical structure type: main_house, adu, condo_unit, apartment, etc."
    )

    # ==========================================================================
    # DWELLING USE (HOW is it used?)
    # ==========================================================================
    dwelling_use: Mapped[DwellingUse | None] = mapped_column(
        SQLEnum(DwellingUse), index=True,
        doc="Occupancy pattern: full_time_residence, second_home, short_term_rental, vacant"
    )

    # ==========================================================================
    # OWNER OCCUPANCY (WHO lives here?)
    # ==========================================================================
    is_owner_occupied: Mapped[bool | None] = mapped_column(
        Boolean,
        doc="For FULL_TIME_RESIDENCE: True=owner lives here (HOMESTEAD), "
            "False=tenant lives here (LTR→NHS_NR). None if unknown or N/A."
    )

    # ==========================================================================
    # PHYSICAL CHARACTERISTICS
    # ==========================================================================
    bedrooms: Mapped[int | None] = mapped_column(
        Integer,
        doc="Number of bedrooms. Source: STR listing, manual entry. "
            "Grand List doesn't provide this."
    )
    bathrooms: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 1),
        doc="Number of bathrooms (0.5 = half bath)"
    )
    square_feet: Mapped[int | None] = mapped_column(
        Integer,
        doc="Living area in square feet"
    )
    year_built: Mapped[int | None] = mapped_column(
        Integer,
        doc="Year the dwelling was built"
    )
    assessed_value: Mapped[int | None] = mapped_column(
        Integer,
        doc="Assessed value for this unit (from Grand List REAL_FLV)"
    )

    # ==========================================================================
    # ACT 73 HABITABILITY REQUIREMENTS
    # ==========================================================================
    has_separate_entrance: Mapped[bool] = mapped_column(Boolean, default=True)
    has_sleeping_facilities: Mapped[bool] = mapped_column(Boolean, default=True)
    has_cooking_facilities: Mapped[bool] = mapped_column(Boolean, default=True)
    has_sanitary_facilities: Mapped[bool] = mapped_column(Boolean, default=True)
    is_year_round_habitable: Mapped[bool] = mapped_column(
        Boolean, default=True,
        doc="If False (e.g., uninsulated camp), not a 'dwelling' under Act 73"
    )

    # ==========================================================================
    # HOMESTEAD FILING (from Grand List)
    # ==========================================================================
    homestead_filed: Mapped[bool] = mapped_column(
        Boolean, default=False,
        doc="True if homestead declaration filed for this unit. "
            "Strong signal of FULL_TIME_RESIDENCE + is_owner_occupied=True"
    )

    # ==========================================================================
    # RESIDENCY TRACKING
    # ==========================================================================
    resident_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("people.id"),
        doc="Person who resides here (if known and in people table)"
    )
    resident_since: Mapped[date | None] = mapped_column(
        Date,
        doc="When the current resident moved in"
    )
    occupant_name: Mapped[str | None] = mapped_column(
        Text,
        doc="Occupant name if different from owner or not in people table"
    )
    occupant_state: Mapped[str | None] = mapped_column(
        String(50),
        doc="Mailing state/country of occupant (for out-of-state tracking)"
    )

    # ==========================================================================
    # STR LINKAGE (SEPARATE DATA - not a classification!)
    # ==========================================================================
    str_listing_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("str_listings.id"),
        doc="Matched STR listing for this dwelling. ANY dwelling can have this - "
            "even FULL_TIME_RESIDENCE (homeowner rents occasionally). "
            "dwelling_use=SHORT_TERM_RENTAL means STR is the PRIMARY use."
    )

    # ==========================================================================
    # ATTESTATION TRACKING (Act 73, starting 2028)
    # ==========================================================================
    last_attestation_date: Mapped[datetime | None] = mapped_column(DateTime)
    attestation_filing_year: Mapped[int | None] = mapped_column(Integer)

    # ==========================================================================
    # METADATA
    # ==========================================================================
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    data_source: Mapped[str | None] = mapped_column(
        String(50),
        doc="How identified: 'grand_list', 'str_inference', 'manual', 'attestation'"
    )
    source_confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 2),
        doc="Confidence in this data (0.00-1.00)"
    )
    notes: Mapped[str | None] = mapped_column(Text)

    # ==========================================================================
    # RELATIONSHIPS
    # ==========================================================================
    parcel: Mapped["Parcel"] = relationship("Parcel", back_populates="dwellings")
    str_listing: Mapped["STRListing | None"] = relationship("STRListing")
    resident: Mapped["Person | None"] = relationship("Person", foreign_keys=[resident_id])
    property_ownerships: Mapped[list["PropertyOwnership"]] = relationship(
        "PropertyOwnership", back_populates="dwelling"
    )

    def __repr__(self) -> str:
        unit = f" {self.unit_number}" if self.unit_number else ""
        dtype = self.dwelling_type.value if self.dwelling_type else "?"
        use = self.dwelling_use.value if self.dwelling_use else "?"
        return f"<Dwelling{unit} {dtype}/{use} @ {self.parcel_id}>"

    # ==========================================================================
    # COMPUTED PROPERTIES
    # ==========================================================================

    @property
    def is_habitable_dwelling(self) -> bool:
        """True if this meets Act 73 dwelling definition (all habitability requirements)."""
        return all([
            self.has_separate_entrance,
            self.has_sleeping_facilities,
            self.has_cooking_facilities,
            self.has_sanitary_facilities,
            self.is_year_round_habitable,
        ])

    @property
    def tax_classification(self) -> TaxClassification | None:
        """Derive Act 73 tax classification from dwelling_use + is_owner_occupied.

        Classification Logic:
        - FULL_TIME_RESIDENCE + is_owner_occupied=True → HOMESTEAD
        - FULL_TIME_RESIDENCE + is_owner_occupied=False → NHS_NONRESIDENTIAL (LTR)
        - SECOND_HOME, SHORT_TERM_RENTAL, VACANT → NHS_RESIDENTIAL
        - SEASONAL, COMMERCIAL → NHS_NONRESIDENTIAL

        Note: 5+ unit buildings are NHS_NONRESIDENTIAL regardless of use,
        but that check requires parcel-level context.
        """
        if not self.dwelling_use:
            return None

        if self.dwelling_use == DwellingUse.FULL_TIME_RESIDENCE:
            if self.is_owner_occupied is True:
                return TaxClassification.HOMESTEAD
            elif self.is_owner_occupied is False:
                return TaxClassification.NHS_NONRESIDENTIAL  # Long-term rental
            else:
                return None  # Unknown

        if self.dwelling_use in [
            DwellingUse.SECOND_HOME,
            DwellingUse.SHORT_TERM_RENTAL,
            DwellingUse.VACANT,
        ]:
            return TaxClassification.NHS_RESIDENTIAL

        if self.dwelling_use in [DwellingUse.SEASONAL, DwellingUse.COMMERCIAL]:
            return TaxClassification.NHS_NONRESIDENTIAL

        return None

    @property
    def is_homestead(self) -> bool:
        """True if this is owner's primary residence (HOMESTEAD classification)."""
        return self.tax_classification == TaxClassification.HOMESTEAD

    @property
    def has_str_listing(self) -> bool:
        """True if this dwelling has a matched STR listing (separate from use!)."""
        return self.str_listing_id is not None

    @property
    def is_primary_str(self) -> bool:
        """True if SHORT_TERM_RENTAL is the primary use (not just occasional hosting)."""
        return self.dwelling_use == DwellingUse.SHORT_TERM_RENTAL

    @property
    def adds_to_housing_supply(self) -> bool | None:
        """True if someone lives here year-round (adds to local housing supply).

        Only FULL_TIME_RESIDENCE adds to housing supply - someone actually lives here.
        SECOND_HOME, STR, VACANT all represent housing removed from local supply.
        """
        if not self.dwelling_use:
            return None
        return self.dwelling_use == DwellingUse.FULL_TIME_RESIDENCE


class DwellingAttestation(Base):
    """Annual dwelling use attestation required by Act 73 starting 2028.

    Property owners with 1-4 dwelling units must file annually declaring:
    - Use of each dwelling (owner-occupied, rental, vacant, etc.)
    - Rental periods and durations
    - Owner domicile status
    """

    __tablename__ = "dwelling_attestations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Link to dwelling
    dwelling_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dwellings.id"), nullable=False, index=True
    )

    # Filing info
    filing_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    filed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    filed_by: Mapped[str | None] = mapped_column(Text)  # Filer name

    # Declared use (same as Dwelling.dwelling_use)
    declared_use: Mapped[DwellingUse] = mapped_column(
        SQLEnum(DwellingUse), nullable=False,
        doc="Owner's declared use: full_time_residence, second_home, short_term_rental, etc."
    )

    # Owner occupancy (same as Dwelling.is_owner_occupied)
    is_owner_occupied: Mapped[bool | None] = mapped_column(
        Boolean,
        doc="For FULL_TIME_RESIDENCE: True=owner lives here, False=tenant"
    )

    # For rental properties
    is_long_term_rental: Mapped[bool] = mapped_column(Boolean, default=False)
    rental_months_per_year: Mapped[int | None] = mapped_column(Integer)
    typical_rental_duration_days: Mapped[int | None] = mapped_column(Integer)

    # Domicile declaration
    is_filer_domicile: Mapped[bool] = mapped_column(Boolean, default=False)
    months_occupied_by_filer: Mapped[int | None] = mapped_column(Integer)

    # Resulting classification (derived from declared_use + is_owner_occupied)
    resulting_tax_class: Mapped[TaxClassification | None] = mapped_column(
        SQLEnum(TaxClassification),
        doc="Tax classification derived from attestation: HOMESTEAD, NHS_RESIDENTIAL, NHS_NONRESIDENTIAL"
    )

    # Relationships
    dwelling: Mapped["Dwelling"] = relationship("Dwelling")

    __table_args__ = (
        Index('ix_attestation_dwelling_year', 'dwelling_id', 'filing_year', unique=True),
    )

    def __repr__(self) -> str:
        return f"<DwellingAttestation {self.filing_year} {self.declared_use}>"
