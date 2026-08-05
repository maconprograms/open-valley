"""Create versioned, strictly redacted public release bundles."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from pydantic import ValidationError

from .public_schema import (
    PUBLIC_RELEASE_SCHEMA_VERSION,
    RELEASE_VERSION,
    PublicHomesteadTrend,
    PublicManifest,
    PublicMap,
    PublicProviders,
    PublicReleasePointer,
    PublicSummary,
)
from .schema import SourceRun

REQUIRED_ARTIFACTS = {
    "summary": "summary.json",
    "homestead_trend": "homestead-trend.json",
    "providers": "providers.json",
    "map": "map.geojson",
}
RESTRICTED_FIELD_TOKENS = {
    "owner",
    "owners",
    "owner_text",
    "owner_position",
    "mailing",
    "mailing_address",
    "mailing_city",
    "mailing_state",
    "mailing_zip",
    "review",
    "reviews",
    "reviewed_by",
    "evidence_summary",
    "raw",
    "raw_values",
    "payload",
    "source_extract",
    "source_key",
    "private",
    "protected",
    "connection_string",
    "database_url",
}
_SENSITIVE_VALUE_FIELD = re.compile(
    r"(?:owner|mailing|review|raw|payload|seller|buyer|party|evidence_summary)", re.I
)
CANONICAL_PUBLIC_VALUE_FIELDS = frozenset(
    {
        "town",
        "schema_version",
        "release_version",
        "source_run_id",
        "release_id",
        "retrieved_timezone",
        "provider",
        "provider_url",
        "label",
        "sha256",
        "aggregate_checksum",
        "measure",
        "tax_status_bucket",
        "gis_match",
    }
)


class PublicReleaseError(RuntimeError):
    """A public artifact could not be safely generated."""


class PublicReleaseSafetyError(PublicReleaseError):
    """An output contains an allowlist violation without disclosing its value."""

    def __init__(self, artifact_path: str, field_path: str):
        self.artifact_path = artifact_path
        self.field_path = field_path
        super().__init__(f"unsafe public release artifact: {artifact_path} {field_path}")


@dataclass(frozen=True)
class PublicReleaseReceipt:
    town: str
    source_run_id: str
    release_id: str
    release_directory: Path


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _town_key(town: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "-", town.lower()).strip("-")
    if not key:
        raise PublicReleaseError("invalid public release town")
    return key


def _safe_error(artifact: str) -> PublicReleaseError:
    return PublicReleaseError(f"invalid public release artifact: {artifact}")


def _validate(model: type[Any], payload: dict[str, Any], artifact: str) -> dict[str, Any]:
    try:
        return model.model_validate(payload).model_dump(mode="json")
    except ValidationError as error:
        raise _safe_error(artifact) from error


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _safe_provider_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.netloc:
        return None
    return urlunsplit((parsed.scheme, parsed.netloc, "/", "", ""))


def _tax_status(assessment: Mapping[str, Any] | None) -> str:
    if assessment and assessment.get("homestead_filed") is True:
        return "homestead_filed"
    if assessment and assessment.get("homestead_filed") is False:
        return "non_homestead"
    return "unknown"


def _first_by_account(records: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    values: dict[str, Mapping[str, Any]] = {}
    for record in records:
        account_id = record.get("account_id")
        if isinstance(account_id, str):
            values.setdefault(account_id, record)
    return values


def _protected_values(records_by_type: Mapping[str, Sequence[Mapping[str, Any]]]) -> set[str]:
    """Collect private values only for comparison; never return or log them."""

    values: set[str] = set()

    def visit(value: Any, key: str | None = None) -> None:
        if isinstance(value, Mapping):
            for child_key, child_value in value.items():
                visit(child_value, str(child_key))
        elif isinstance(value, list):
            for child in value:
                visit(child, key)
        elif isinstance(value, str) and key and _SENSITIVE_VALUE_FIELD.search(key):
            normalized = value.strip().casefold()
            if normalized:
                values.add(normalized)

    for records in records_by_type.values():
        for record in records:
            visit(record)
    return values


def scan_public_artifact(
    payload: Any, artifact_path: str, protected_values: set[str] | None = None
) -> None:
    """Fail closed on restricted keys or known protected values.

    The only diagnostics are the public artifact and public field path.  Source
    values and validation exception text must never enter logs or API errors.
    """

    protected_values = protected_values or set()

    def visit(value: Any, path: str) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                key_text = str(key)
                child_path = f"{path}.{key_text}" if path else key_text
                if key_text.casefold() in RESTRICTED_FIELD_TOKENS:
                    raise PublicReleaseSafetyError(artifact_path, child_path)
                visit(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")
        elif (
            isinstance(value, str)
            and path.rsplit(".", 1)[-1] not in CANONICAL_PUBLIC_VALUE_FIELDS
            and value.strip().casefold() in protected_values
        ):
            raise PublicReleaseSafetyError(artifact_path, path)

    visit(payload, "")


def _validate_coverage(
    accounts: Sequence[Mapping[str, Any]],
    geometries: Sequence[Mapping[str, Any]],
    assessments: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    account_ids = {record.get("id") for record in accounts if isinstance(record.get("id"), str)}
    matched = {
        record.get("account_id")
        for record in geometries
        if record.get("account_id") in account_ids and record.get("geometry") is not None
    }
    known_homestead = {
        record.get("account_id")
        for record in assessments
        if record.get("account_id") in account_ids
        and isinstance(record.get("homestead_filed"), bool)
    }
    denominator = len(account_ids)
    coverage = {
        "accounts_denominator": denominator,
        "matched_geometries": len(matched),
        "geometry_denominator": denominator,
        "known_homestead": len(known_homestead),
        "homestead_denominator": denominator,
    }
    if not denominator or len(matched) / denominator < 0.96 or len(known_homestead) / denominator < 0.96:
        raise PublicReleaseError("public release coverage does not meet the required bar")
    return coverage


def _provider_descriptors(
    records_by_type: Mapping[str, Sequence[Mapping[str, Any]]],
    source_run: SourceRun,
) -> list[dict[str, Any]]:
    providers: dict[str, dict[str, Any]] = {}
    for records in records_by_type.values():
        for record in records:
            source = record.get("source")
            if not isinstance(source, Mapping):
                continue
            source_key = source.get("source_key")
            provider_url = _safe_provider_url(source.get("source_url"))
            if not isinstance(source_key, str) or not provider_url:
                continue
            provider = _town_key(source_key.split(":", 1)[0])
            item = providers.setdefault(
                provider,
                {"provider": provider, "provider_url": provider_url},
            )
    if not providers:
        raise PublicReleaseError("public release has no safe provider descriptors")
    result = []
    for provider, item in sorted(providers.items()):
        scope = "Aggregate public release metadata only"
        result.append(
            {
                "provider": provider,
                "provider_url": item["provider_url"],
                "retrieved_at": source_run.retrieved_at,
                "retrieved_timezone": "UTC",
                "aggregate_checksum": _sha256(
                    {"provider": provider, "provider_url": item["provider_url"], "scope": scope}
                ),
                "scope": scope,
            }
        )
    return result


def _build_artifacts(
    source_run: SourceRun, records_by_type: Mapping[str, Sequence[Mapping[str, Any]]]
) -> dict[str, tuple[type[Any], dict[str, Any]]]:
    accounts = records_by_type.get("property_accounts", [])
    geometries = records_by_type.get("parcel_geometries", [])
    assessments = records_by_type.get("assessment_snapshots", [])
    units = records_by_type.get("housing_unit_claims", [])
    coverage = _validate_coverage(accounts, geometries, assessments)
    assessments_by_account = _first_by_account(assessments)
    units_by_account: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for unit in units:
        if isinstance(unit.get("account_id"), str):
            units_by_account[unit["account_id"]].append(unit)
    accounts_by_id = {
        record["id"] for record in accounts if isinstance(record.get("id"), str)
    }
    features: list[dict[str, Any]] = []
    for geometry in geometries:
        account_id = geometry.get("account_id")
        shape = geometry.get("geometry")
        if account_id not in accounts_by_id or not isinstance(shape, Mapping):
            continue
        account = next(record for record in accounts if record.get("id") == account_id)
        unit_claims = units_by_account.get(account_id, [])
        features.append(
            {
                "type": "Feature",
                "geometry": shape,
                "properties": {
                    "address": account.get("address"),
                    "gis_match": geometry.get("link_confidence", "unmatched"),
                    "tax_status_bucket": _tax_status(assessments_by_account.get(account_id)),
                    "housing_unit_claims": len(unit_claims),
                    "unit_evidence_levels": sorted(
                        {claim.get("evidence_level", "unknown") for claim in unit_claims}
                    ),
                },
            }
        )
    tax_status = Counter(
        _tax_status(assessments_by_account.get(account_id)) for account_id in accounts_by_id
    )
    trend: dict[int, Counter[str]] = defaultdict(Counter)
    for account_id in accounts_by_id:
        assessment = assessments_by_account.get(account_id)
        if not assessment or not isinstance(assessment.get("grand_list_year"), int):
            continue
        counts = trend[assessment["grand_list_year"]]
        counts["tax_accounts"] += 1
        if assessment.get("homestead_filed") is True:
            counts["homestead_filed"] += 1
        if assessment.get("homestead_filed") is None:
            counts["unknown_homestead"] += 1
    common = {
        "schema_version": PUBLIC_RELEASE_SCHEMA_VERSION,
        "release_version": RELEASE_VERSION,
        "town": source_run.town,
        "source_run_id": source_run.id,
    }
    aggregate_input_checksum = _sha256(source_run.input_checksums)
    return {
        "summary.json": (
            PublicSummary,
            {
                **common,
                "coverage": coverage,
                "counts": {"tax_accounts": len(accounts_by_id), "housing_unit_claims": len(units)},
                "tax_status_buckets": {
                    "homestead_filed": tax_status["homestead_filed"],
                    "non_homestead": tax_status["non_homestead"],
                    "unknown": tax_status["unknown"],
                },
            },
        ),
        "homestead-trend.json": (
            PublicHomesteadTrend,
            {
                **common,
                "measure": "HSDECL filing observation among available tax accounts",
                "observations": [
                    {
                        "grand_list_year": year,
                        "tax_accounts": trend[year]["tax_accounts"],
                        "homestead_filed": trend[year]["homestead_filed"],
                        "unknown_homestead": trend[year]["unknown_homestead"],
                    }
                    for year in sorted(trend)
                ],
            },
        ),
        "providers.json": (
            PublicProviders,
            {**common, "providers": _provider_descriptors(records_by_type, source_run)},
        ),
        "map.geojson": (
            PublicMap,
            {"type": "FeatureCollection", **common, "features": features},
        ),
        "manifest.json": (
            PublicManifest,
            {
                **common,
                "retrieved_at": source_run.retrieved_at,
                "retrieved_timezone": "UTC",
                "input_checksums": [{"label": "private-input-set", "sha256": aggregate_input_checksum}],
                "coverage": coverage,
                "artifacts": REQUIRED_ARTIFACTS,
            },
        ),
    }


def export_public_release(
    source_run: SourceRun | Mapping[str, Any],
    records_by_type: Mapping[str, Sequence[Mapping[str, Any]]],
    releases_root: Path,
    *,
    now: datetime | None = None,
) -> PublicReleaseReceipt:
    """Export a safe bundle and atomically point the town at it on success."""

    try:
        run = source_run if isinstance(source_run, SourceRun) else SourceRun.model_validate(source_run)
    except ValidationError as error:
        raise PublicReleaseError("invalid private source run") from error
    if run.status not in {"validated", "promoted"}:
        raise PublicReleaseError("only validated source runs may be released")
    now = now or datetime.now(UTC)
    retrieved_at = run.retrieved_at.astimezone(UTC)
    if now - retrieved_at > timedelta(days=90):
        raise PublicReleaseError("source run is stale without a public stale notice")
    town_key = _town_key(run.town)
    release_id = f"{run.id}--{RELEASE_VERSION}"
    town_root = releases_root / town_key
    destination = town_root / release_id
    if destination.exists():
        raise PublicReleaseError("public release version already exists")
    protected_values = _protected_values(records_by_type)
    artifacts = _build_artifacts(run, records_by_type)
    releases_root.mkdir(parents=True, exist_ok=True)
    staging_root = Path(tempfile.mkdtemp(prefix=".public-release-", dir=releases_root))
    staging_release = staging_root / release_id
    try:
        staging_release.mkdir()
        for artifact, (model, payload) in artifacts.items():
            validated = _validate(model, payload, artifact)
            scan_public_artifact(validated, artifact, protected_values)
            _write_json(staging_release / artifact, validated)
        town_root.mkdir(parents=True, exist_ok=True)
        os.replace(staging_release, destination)
        pointer = _validate(
            PublicReleasePointer,
            {
                "schema_version": PUBLIC_RELEASE_SCHEMA_VERSION,
                "town": run.town,
                "release_id": release_id,
                "source_run_id": run.id,
                "release_version": RELEASE_VERSION,
            },
            "current.json",
        )
        scan_public_artifact(pointer, "current.json", protected_values)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=town_root, delete=False) as file:
            json.dump(pointer, file, indent=2, sort_keys=True)
            file.write("\n")
            pointer_temp = Path(file.name)
        os.replace(pointer_temp, town_root / "current.json")
    except Exception:
        shutil.rmtree(staging_root, ignore_errors=True)
        if destination.exists() and not (town_root / "current.json").exists():
            shutil.rmtree(destination, ignore_errors=True)
        raise
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)
    return PublicReleaseReceipt(run.town, run.id, release_id, destination)
