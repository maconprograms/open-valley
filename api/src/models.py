"""SQLAlchemy models for Warren community data."""

import uuid
from datetime import datetime
from decimal import Decimal

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


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
    tax_status: Mapped[list["TaxStatus"]] = relationship("TaxStatus", back_populates="parcel")

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

    # Relationships
    issue: Mapped["FPFIssue"] = relationship("FPFIssue", back_populates="posts")
    person: Mapped["FPFPerson"] = relationship("FPFPerson", back_populates="posts")

    def __repr__(self) -> str:
        return f"<FPFPost {self.title[:30]}>"


class Organization(Base):
    """An organization mentioned in FPF posts or community data."""

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    org_type: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(Text)
    town: Mapped[str | None] = mapped_column(String(50), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Organization {self.name}>"
