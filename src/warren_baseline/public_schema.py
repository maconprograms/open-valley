"""Strict, redacted schemas for artifacts that may enter the public release.

These models deliberately describe a smaller data product than the private
ledger.  They are an allowlist: unknown fields are errors at every object
boundary, rather than fields that a future source change can silently publish.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


PUBLIC_RELEASE_SCHEMA_VERSION = "openvalley-public-release/v1"
RELEASE_VERSION = "v1"


class PublicArtifact(BaseModel):
    """Base class for public JSON artifacts; reject every unapproved key."""

    model_config = ConfigDict(extra="forbid")


class PublicCoverage(PublicArtifact):
    accounts_denominator: int = Field(ge=0)
    matched_geometries: int = Field(ge=0)
    geometry_denominator: int = Field(ge=0)
    known_homestead: int = Field(ge=0)
    homestead_denominator: int = Field(ge=0)

    @model_validator(mode="after")
    def counts_do_not_exceed_denominators(self) -> "PublicCoverage":
        if self.matched_geometries > self.geometry_denominator:
            raise ValueError("geometry coverage is invalid")
        if self.known_homestead > self.homestead_denominator:
            raise ValueError("homestead coverage is invalid")
        return self


class AggregateChecksum(PublicArtifact):
    label: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class ReleaseArtifacts(PublicArtifact):
    summary: Literal["summary.json"]
    homestead_trend: Literal["homestead-trend.json"]
    providers: Literal["providers.json"]
    map: Literal["map.geojson"]


class PublicManifest(PublicArtifact):
    schema_version: Literal[PUBLIC_RELEASE_SCHEMA_VERSION]
    release_version: Literal[RELEASE_VERSION]
    town: str = Field(min_length=1, max_length=80)
    source_run_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,127}$")
    retrieved_at: datetime
    retrieved_timezone: Literal["UTC"]
    input_checksums: list[AggregateChecksum] = Field(min_length=1)
    coverage: PublicCoverage
    artifacts: ReleaseArtifacts


class PublicSummaryCounts(PublicArtifact):
    tax_accounts: int = Field(ge=0)
    housing_unit_claims: int = Field(ge=0)


class PublicTaxStatusBuckets(PublicArtifact):
    homestead_filed: int = Field(ge=0)
    non_homestead: int = Field(ge=0)
    unknown: int = Field(ge=0)


class PublicSummary(PublicArtifact):
    schema_version: Literal[PUBLIC_RELEASE_SCHEMA_VERSION]
    release_version: Literal[RELEASE_VERSION]
    town: str = Field(min_length=1, max_length=80)
    source_run_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,127}$")
    coverage: PublicCoverage
    counts: PublicSummaryCounts
    tax_status_buckets: PublicTaxStatusBuckets


class PublicTrendObservation(PublicArtifact):
    grand_list_year: int = Field(ge=1900, le=3000)
    tax_accounts: int = Field(ge=0)
    homestead_filed: int = Field(ge=0)
    unknown_homestead: int = Field(ge=0)

    @model_validator(mode="after")
    def counts_are_consistent(self) -> "PublicTrendObservation":
        if self.homestead_filed + self.unknown_homestead > self.tax_accounts:
            raise ValueError("trend counts are invalid")
        return self


class PublicHomesteadTrend(PublicArtifact):
    schema_version: Literal[PUBLIC_RELEASE_SCHEMA_VERSION]
    release_version: Literal[RELEASE_VERSION]
    town: str = Field(min_length=1, max_length=80)
    source_run_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,127}$")
    measure: Literal["HSDECL filing observation among available tax accounts"]
    observations: list[PublicTrendObservation]


class PublicProviderDescriptor(PublicArtifact):
    """Provider-level provenance; it deliberately has no row-level locator."""

    provider: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")
    provider_url: str = Field(min_length=8, max_length=2048)
    retrieved_at: datetime
    retrieved_timezone: Literal["UTC"]
    aggregate_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    field_labels: list[str] = Field(min_length=1, max_length=100)

    @field_validator("provider_url")
    @classmethod
    def provider_url_has_no_property_locator(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("provider URL must be an HTTPS collection URL")
        if "{" in value or "}" in value:
            raise ValueError("provider URL must not be templated")
        return value

    @field_validator("field_labels")
    @classmethod
    def field_labels_are_plain_labels(cls, values: list[str]) -> list[str]:
        if any(not value or len(value) > 120 for value in values):
            raise ValueError("provider field labels are invalid")
        return sorted(set(values))


class PublicProviders(PublicArtifact):
    schema_version: Literal[PUBLIC_RELEASE_SCHEMA_VERSION]
    release_version: Literal[RELEASE_VERSION]
    town: str = Field(min_length=1, max_length=80)
    source_run_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,127}$")
    providers: list[PublicProviderDescriptor] = Field(min_length=1)


class PublicGeometry(PublicArtifact):
    type: Literal["Point", "LineString", "Polygon", "MultiPolygon"]
    coordinates: list[Any]

    @field_validator("coordinates")
    @classmethod
    def coordinates_are_only_numbers_and_lists(cls, value: list[Any]) -> list[Any]:
        def valid_coordinate(part: Any) -> bool:
            return isinstance(part, (int, float)) and not isinstance(part, bool) or (
                isinstance(part, list) and bool(part) and all(valid_coordinate(item) for item in part)
            )

        if not valid_coordinate(value):
            raise ValueError("geometry coordinates are invalid")
        return value


class PublicMapProperties(PublicArtifact):
    address: str | None = Field(default=None, max_length=300)
    gis_match: Literal["exact_parcid", "exact_span", "coordinate_only", "unmatched"]
    tax_status_bucket: Literal["homestead_filed", "non_homestead", "unknown"]
    housing_unit_claims: int = Field(ge=0)
    unit_evidence_levels: list[Literal["documented", "inferred", "unknown", "excluded"]]


class PublicMapFeature(PublicArtifact):
    type: Literal["Feature"]
    geometry: PublicGeometry
    properties: PublicMapProperties


class PublicMap(PublicArtifact):
    type: Literal["FeatureCollection"]
    schema_version: Literal[PUBLIC_RELEASE_SCHEMA_VERSION]
    release_version: Literal[RELEASE_VERSION]
    town: str = Field(min_length=1, max_length=80)
    source_run_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,127}$")
    features: list[PublicMapFeature]


class PublicReleasePointer(PublicArtifact):
    schema_version: Literal[PUBLIC_RELEASE_SCHEMA_VERSION]
    town: str = Field(min_length=1, max_length=80)
    release_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,160}$")
    source_run_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,127}$")
    release_version: Literal[RELEASE_VERSION]
