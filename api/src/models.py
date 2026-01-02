"""SQLAlchemy models for Warren community data.

Data Architecture Overview:
- Person is the CENTRAL ENTITY connecting property, community, and organizations
- Medallion Architecture: Bronze (raw) → Silver (validated) → Gold (aggregates)
- All changes tracked via ChangeLog audit trail

Key References:
- Vermont Act 73 (2025): Three-class dwelling tax system
- RP-1354 Legislative Report: Dwelling classification guidance
- See docs/DATA_ARCHITECTURE.md for full design
- See src/schemas.py for Pydantic validation models
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum as PyEnum

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
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from .database import Base


# =============================================================================
# ENUMS
# =============================================================================


class OrganizationType(str, PyEnum):
    """Types of organizations that can own property or have members.

    Property-Owning Entities:
    - LLC: Limited Liability Company (cannot file homestead)
    - TRUST: Trust with individual beneficiary (may allow homestead)
    - CORPORATION: Inc., Corp. (cannot file homestead)

    Community Bodies:
    - GOVERNMENT: Town bodies (Planning Commission, Selectboard)
    - NONPROFIT: 501(c)(3) organizations
    - ASSOCIATION: HOAs, neighborhood groups
    """
    LLC = "llc"
    TRUST = "trust"
    CORPORATION = "corporation"
    GOVERNMENT = "government"
    NONPROFIT = "nonprofit"
    ASSOCIATION = "association"
    OTHER = "other"


class OwnershipType(str, PyEnum):
    """Type of property ownership interest."""
    FEE_SIMPLE = "fee_simple"
    LIFE_ESTATE = "life_estate"
    TRUST_BENEFICIARY = "trust_beneficiary"
    JOINT_TENANCY = "joint_tenancy"
    TENANCY_IN_COMMON = "tenancy_in_common"


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
    year_built: Mapped[int | None] = mapped_column(Integer)
    lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    geometry: Mapped[str | None] = mapped_column(Geometry("MULTIPOLYGON", srid=4326))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    owners: Mapped[list["Owner"]] = relationship("Owner", back_populates="parcel")
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


class Owner(Base):
    """An owner of a parcel."""

    __tablename__ = "owners"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    parcel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parcels.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    owner_type: Mapped[str | None] = mapped_column(String(20))  # individual, trust, llc, estate
    mailing_address: Mapped[str | None] = mapped_column(Text)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    parcel: Mapped["Parcel"] = relationship("Parcel", back_populates="owners")

    def __repr__(self) -> str:
        return f"<Owner {self.name}>"


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

    Replaces the simpler Owner table with structured ownership tracking.
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
    ownership_type: Mapped[str] = mapped_column(
        String(50), default="fee_simple",
        doc="Type: fee_simple, life_estate, trust_beneficiary, etc."
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
# DWELLING LAYER: Act 73 Multi-Dwelling Support
# A parcel can contain multiple dwelling units, each classified independently
# -----------------------------------------------------------------------------


class Dwelling(Base):
    """A single dwelling unit within a parcel.

    Vermont Act 73 (2025) defines a dwelling as:
    - Building or part of building with separate ingress/egress
    - Designed for occupancy with living facilities (sleeping, cooking, sanitary)
    - Fit for year-round habitation

    Tax classifications under Act 73:
    - HOMESTEAD: Owner's domicile for 6+ months/year
    - NHS_RESIDENTIAL: Second homes, STRs, vacant year-round dwellings (1-4 units)
    - NHS_NONRESIDENTIAL: Commercial, long-term rentals, 5+ unit buildings, seasonal

    A parcel can contain 1-N dwellings, each classified independently.
    """

    __tablename__ = "dwellings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Link to parcel (many dwellings can be in one parcel)
    parcel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parcels.id"), nullable=False, index=True
    )

    # Dwelling identification within parcel
    unit_number: Mapped[str | None] = mapped_column(String(20))  # "A", "B", "Unit 1", etc.
    unit_address: Mapped[str | None] = mapped_column(Text)  # Full address if different from parcel

    # Physical characteristics
    bedrooms: Mapped[int | None] = mapped_column(Integer)
    bathrooms: Mapped[Decimal | None] = mapped_column(Numeric(3, 1))
    square_feet: Mapped[int | None] = mapped_column(Integer)
    year_built: Mapped[int | None] = mapped_column(Integer)

    # Value (from Grand List - per-unit for condos)
    assessed_value: Mapped[int | None] = mapped_column(
        Integer,
        doc="Assessed value for this dwelling unit (from REAL_FLV)"
    )

    # Habitability (Act 73 requirements)
    has_separate_entrance: Mapped[bool] = mapped_column(Boolean, default=True)
    has_sleeping_facilities: Mapped[bool] = mapped_column(Boolean, default=True)
    has_cooking_facilities: Mapped[bool] = mapped_column(Boolean, default=True)
    has_sanitary_facilities: Mapped[bool] = mapped_column(Boolean, default=True)
    is_year_round_habitable: Mapped[bool] = mapped_column(Boolean, default=True)

    # Homestead status (from Grand List HSDECL - per-unit for condos)
    homestead_filed: Mapped[bool] = mapped_column(
        Boolean, default=False,
        doc="True if homestead declaration filed for this unit"
    )

    # Tax classification (Act 73 three-class system)
    tax_classification: Mapped[str | None] = mapped_column(
        String(30), index=True
    )  # HOMESTEAD, NHS_RESIDENTIAL, NHS_NONRESIDENTIAL

    # Current use (more granular than tax class)
    use_type: Mapped[str | None] = mapped_column(
        String(50)
    )  # owner_occupied_primary, owner_occupied_secondary, long_term_rental, short_term_rental, vacant, seasonal

    # Who lives here (key for residency tracking)
    resident_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("people.id"),
        doc="Person who resides in this dwelling (if known)"
    )
    resident_since: Mapped[date | None] = mapped_column(
        Date,
        doc="When the current resident moved in"
    )

    # Owner/occupant info (if different from parcel owner, or if resident not in people table)
    occupant_name: Mapped[str | None] = mapped_column(Text)
    occupant_state: Mapped[str | None] = mapped_column(String(50))  # Mailing state/country

    # STR linkage (if this dwelling is an STR)
    str_listing_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("str_listings.id"), nullable=True
    )

    # Attestation tracking (Act 73 requirement starting 2028)
    last_attestation_date: Mapped[datetime | None] = mapped_column(DateTime)
    attestation_filing_year: Mapped[int | None] = mapped_column(Integer)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    data_source: Mapped[str | None] = mapped_column(String(50))  # "grand_list", "str_inference", "manual"
    notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    parcel: Mapped["Parcel"] = relationship("Parcel", back_populates="dwellings")
    str_listing: Mapped["STRListing | None"] = relationship("STRListing")
    resident: Mapped["Person | None"] = relationship("Person", foreign_keys=[resident_id])
    property_ownerships: Mapped[list["PropertyOwnership"]] = relationship(
        "PropertyOwnership", back_populates="dwelling"
    )

    def __repr__(self) -> str:
        unit = f" {self.unit_number}" if self.unit_number else ""
        return f"<Dwelling{unit} {self.use_type} @ parcel {self.parcel_id}>"

    @property
    def is_habitable_dwelling(self) -> bool:
        """Check if this meets Act 73 dwelling definition."""
        return all([
            self.has_separate_entrance,
            self.has_sleeping_facilities,
            self.has_cooking_facilities,
            self.has_sanitary_facilities,
            self.is_year_round_habitable,
        ])

    @property
    def is_primary_residence(self) -> bool:
        """True if this is owner's primary residence (homestead)."""
        return self.tax_classification == "HOMESTEAD"

    @property
    def is_str(self) -> bool:
        """True if this dwelling is used as short-term rental."""
        return self.use_type == "short_term_rental" or self.str_listing_id is not None


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

    # Declared use
    declared_use: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # Same values as Dwelling.use_type

    # For rental properties
    is_long_term_rental: Mapped[bool] = mapped_column(Boolean, default=False)
    rental_months_per_year: Mapped[int | None] = mapped_column(Integer)
    typical_rental_duration_days: Mapped[int | None] = mapped_column(Integer)

    # Domicile declaration
    is_filer_domicile: Mapped[bool] = mapped_column(Boolean, default=False)
    months_occupied_by_filer: Mapped[int | None] = mapped_column(Integer)

    # Resulting classification
    resulting_tax_class: Mapped[str | None] = mapped_column(String(30))

    # Relationships
    dwelling: Mapped["Dwelling"] = relationship("Dwelling")

    __table_args__ = (
        Index('ix_attestation_dwelling_year', 'dwelling_id', 'filing_year', unique=True),
    )

    def __repr__(self) -> str:
        return f"<DwellingAttestation {self.filing_year} {self.declared_use}>"
