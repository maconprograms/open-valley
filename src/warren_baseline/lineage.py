"""Stable identifiers and JSONL helpers for immutable baseline source runs."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from .schema import EvidenceRecord


def canonical_account_id(town: str, parcel_id: str) -> str:
    """Return an account key that does not depend on a non-unique SPAN."""
    cleaned_town = re.sub(r"[^a-z0-9]+", "-", town.lower()).strip("-")
    return f"{cleaned_town}:{parcel_id.strip()}"


def normalized_owner_key(owner_text: str) -> str:
    """Normalize only for review/grouping; source text remains canonical."""
    return re.sub(r"[^a-z0-9]+", "-", owner_text.lower()).strip("-")


def source_record_id(source_run_id: str, source_key: str) -> str:
    digest = hashlib.sha256(f"{source_run_id}:{source_key}".encode()).hexdigest()[:16]
    return f"source:{digest}"


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source_file:
        for block in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_now() -> datetime:
    return datetime.now(UTC)


def write_jsonl(path: Path, records: Iterable[EvidenceRecord]) -> None:
    """Write a new immutable run artifact; callers must never overwrite a run."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as output:
        for record in records:
            output.write(record.model_dump_json())
            output.write("\n")


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as source_file:
        return [json.loads(line) for line in source_file if line.strip()]
