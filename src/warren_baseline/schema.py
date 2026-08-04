"""Typed, facts-only records for the Warren baseline evidence ledger.

These records deliberately preserve published observations and their lineage.
They do not infer actual occupancy, residency, or a second-home classification.
"""

from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvidenceRecord(BaseModel):
    """Base model with strict field handling for durable ledger records."""

    model_config = ConfigDict(extra="forbid")


class UnitEvidenceLevel(StrEnum):
    DOCUMENTED = "documented"
    INFERRED = "inferred"
    UNKNOWN = "unknown"
    EXCLUDED = "excluded"


class LinkConfidence(StrEnum):
    EXACT_PARCID = "exact_parcid"
    EXACT_SPAN = "exact_span"
    COORDINATE_ONLY = "coordinate_only"
    UNMATCHED = "unmatched"


class PartyMatchConfidence(StrEnum):
    EXACT = "exact"
    LIKELY = "likely"
    POSSIBLE = "possible"


class PartyMatchReviewState(StrEnum):
    UNREVIEWED = "unreviewed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class ReviewSubject(StrEnum):
    """The source fact or real-world condition a human reviewed."""

    MAILING_ADDRESS = "mailing_address"
    HOMESTEAD_FILING = "homestead_filing"
    OCCUPANCY = "occupancy"


class ReviewStatus(StrEnum):
    """A review result; absence of a record means the account is unreviewed."""

    CONFIRMED = "confirmed"
    CONTRADICTED = "contradicted"
    NEEDS_FOLLOW_UP = "needs_follow_up"


class SourceRun(EvidenceRecord):
    id: str
    town: str
    retrieved_at: datetime
    source_effective_date: date | None = None
    status: Literal["staged", "validated", "promoted", "failed"]
    parser_version: str = "warren-baseline-v1"
    input_checksums: dict[str, str] = Field(default_factory=dict)
    coverage: dict[str, int] = Field(default_factory=dict)
    completed_at: datetime | None = None


class SourceReference(EvidenceRecord):
    """Lineage reference required on every published observation."""

    source_run_id: str
    source_key: str
    source_url: str | None = None
    source_extract: str | None = None
    source_fields: list[str] = Field(min_length=1)
    retrieved_at: datetime
    source_effective_date: date | None = None

    @model_validator(mode="after")
    def has_locator(self) -> "SourceReference":
        if not self.source_url and not self.source_extract:
            raise ValueError("source_url or source_extract is required")
        return self


class SourceRecord(EvidenceRecord):
    id: str
    source: SourceReference
    raw_values: dict[str, Any]


class PropertyAccount(EvidenceRecord):
    """One current NEMRC/VCGI tax account; SPAN intentionally is not unique."""

    id: str
    town: str
    nemrc_parcel_id: str
    parcid: str | None = None
    span: str | None = None
    address: str | None = None
    gis_match: LinkConfidence = LinkConfidence.UNMATCHED
    source: SourceReference


class ParcelGeometry(EvidenceRecord):
    id: str
    account_id: str
    geometry: dict[str, Any] | None = None
    centroid_lon: float | None = None
    centroid_lat: float | None = None
    link_confidence: LinkConfidence
    source: SourceReference


class HousingUnitClaim(EvidenceRecord):
    id: str
    account_id: str
    evidence_level: UnitEvidenceLevel
    evidence_reason: str
    source: SourceReference
    excluded_reason: str | None = None


class AssessmentSnapshot(EvidenceRecord):
    id: str
    account_id: str
    grand_list_year: int | None = None
    homestead_filed: bool | None = None
    property_category: str | None = None
    assessed_total: int | None = None
    assessed_land: int | None = None
    assessed_improvement: int | None = None
    source: SourceReference


class OwnershipObservation(EvidenceRecord):
    id: str
    account_id: str
    owner_text: str
    owner_position: int = Field(default=1, ge=1)
    mailing_address: str | None = None
    mailing_city: str | None = None
    mailing_state: str | None = None
    mailing_zip: str | None = None
    source: SourceReference


class HumanReview(EvidenceRecord):
    """Append-only local review that never replaces a published observation."""

    id: str
    account_id: str
    source_run_id: str
    subject: ReviewSubject
    status: ReviewStatus
    reviewed_at: datetime
    reviewed_by: str
    evidence_summary: str = Field(min_length=1)
    source_observation_ids: list[str] = Field(default_factory=list)


class NormalizedPartyMatch(EvidenceRecord):
    id: str
    ownership_observation_id: str
    normalized_party_key: str
    confidence: PartyMatchConfidence
    review_state: PartyMatchReviewState
    source_owner_text: str


class TransferEvent(EvidenceRecord):
    id: str
    account_id: str | None = None
    source_object_id: str
    transfer_date: date | None = None
    sale_price: int | None = None
    span: str | None = None
    seller_name: str | None = None
    seller_state: str | None = None
    buyer_name: str | None = None
    buyer_state: str | None = None
    buyer_stated_use: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    link_confidence: LinkConfidence
    source: SourceReference
