#!/usr/bin/env python3
"""Fail closed when a public release tree contains private-data surfaces.

Diagnostics deliberately contain only a stable relative artifact path and a
field path. Never print a rejected value, source row, or exception payload.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.warren_baseline.public_schema import (
    PublicHomesteadTrend,
    PublicManifest,
    PublicMap,
    PublicProviders,
    PublicReleasePointer,
    PublicSummary,
)


RAW_PATH_PREFIXES = (
    "data/",
    "private/",
    "raw/",
    "warren/outputs/",
    "warren/reviews/",
    "warren/raw_html/",
    "warren/raw_vcgi_snapshots/",
)
RAW_PATH_EXCEPTIONS = {"data/.gitkeep"}
RESTRICTED_FIELDS = frozenset(
    {
        "owner",
        "owner_name",
        "owner_text",
        "mailing",
        "mailing_address",
        "mailing_city",
        "mailing_state",
        "mailing_zip",
        "review",
        "reviews",
        "review_note",
        "raw_values",
        "raw_payload",
        "source_extract",
        "source_key",
        "source_record",
        "source_records",
        "normalized_party_key",
        "source_owner_text",
        "seller",
        "buyer",
        "party",
    }
)
PUBLIC_ARTIFACT_SUFFIXES = {".geojson", ".json", ".jsonl"}
PUBLIC_ARTIFACT_SCHEMAS = {
    "current.json": PublicReleasePointer,
    "manifest.json": PublicManifest,
    "summary.json": PublicSummary,
    "homestead-trend.json": PublicHomesteadTrend,
    "providers.json": PublicProviders,
    "map.geojson": PublicMap,
}


def tracked_paths(root: Path) -> list[str]:
    """Return Git-tracked paths without ever inspecting untracked data."""

    completed = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=True,
        capture_output=True,
        text=False,
    )
    return sorted(
        path.decode("utf-8")
        for path in completed.stdout.split(b"\0")
        if path
    )


def historical_private_paths(root: Path) -> list[str]:
    """Return only forbidden paths reachable from a public Git ref.

    A deleted raw file remains downloadable from repository history.  This
    check intentionally inspects object names only, never historical content.
    """

    completed = subprocess.run(
        ["git", "-C", str(root), "rev-list", "--objects", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    paths = {
        line.split(" ", 1)[1]
        for line in completed.stdout.splitlines()
        if " " in line
    }
    return sorted(
        path for path in paths
        if path.startswith(RAW_PATH_PREFIXES) and path not in RAW_PATH_EXCEPTIONS
    )


def _field_paths(payload: Any, parent: str = "") -> Iterable[str]:
    if isinstance(payload, dict):
        for key, value in payload.items():
            path = f"{parent}.{key}" if parent else key
            if key.lower() in RESTRICTED_FIELDS:
                yield path
            yield from _field_paths(value, path)
    elif isinstance(payload, list):
        for value in payload:
            yield from _field_paths(value, parent)


def _read_public_json(path: Path) -> list[Any]:
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    return [json.loads(path.read_text(encoding="utf-8"))]


def scan_paths(root: Path, paths: Iterable[str]) -> list[str]:
    """Return safe diagnostics for tracked raw paths and release artifact fields."""

    diagnostics: list[str] = []
    for relative_path in sorted(paths):
        if relative_path.startswith(RAW_PATH_PREFIXES) and relative_path not in RAW_PATH_EXCEPTIONS:
            diagnostics.append(f"{relative_path}: tracked private-data path")
            continue

        if not relative_path.startswith("releases/"):
            continue
        path = root / relative_path
        if path.suffix not in PUBLIC_ARTIFACT_SUFFIXES:
            continue
        schema = PUBLIC_ARTIFACT_SCHEMAS.get(path.name)
        if schema is None or path.suffix == ".jsonl":
            diagnostics.append(f"{relative_path}: unexpected public artifact")
            continue
        try:
            payloads = _read_public_json(path)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            diagnostics.append(f"{relative_path}: invalid public artifact")
            continue
        for payload in payloads:
            try:
                schema.model_validate(payload)
            except ValidationError:
                diagnostics.append(f"{relative_path}: invalid public artifact")
            for field_path in _field_paths(payload):
                diagnostics.append(f"{relative_path}: restricted field {field_path}")
    return diagnostics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    arguments = parser.parse_args(argv)
    root = arguments.root.resolve()
    diagnostics = scan_paths(root, tracked_paths(root))
    diagnostics.extend(
        f"{path}: private-data path remains in reachable Git history"
        for path in historical_private_paths(root)
    )
    if diagnostics:
        print("Public-release guard failed:", file=sys.stderr)
        print(*diagnostics, sep="\n", file=sys.stderr)
        return 1
    print("Public-release guard passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
