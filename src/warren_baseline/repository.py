"""Read only validated, redacted public release artifacts.

This module intentionally has no database or private-ledger dependency.  The
release exporter is the only bridge between protected records and this reader.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from .public_schema import (
    PublicHomesteadTrend,
    PublicManifest,
    PublicMap,
    PublicProviders,
    PublicReleasePointer,
    PublicSummary,
)


class PublicReleaseUnavailableError(RuntimeError):
    """The current public bundle is absent or does not pass its schema checks."""

    def __init__(self) -> None:
        super().__init__("public release unavailable")


REQUIRED_ARTIFACTS: dict[str, type[BaseModel]] = {
    "manifest.json": PublicManifest,
    "summary.json": PublicSummary,
    "homestead-trend.json": PublicHomesteadTrend,
    "providers.json": PublicProviders,
    "map.geojson": PublicMap,
}


class PublicReleaseRepository:
    """Schema-validating, file-backed reader for one town's public release."""

    def __init__(self, root: Path, town_key: str = "warren"):
        self.root = root
        self.town_key = town_key

    @property
    def town_root(self) -> Path:
        return self.root / self.town_key

    @property
    def pointer_path(self) -> Path:
        return self.town_root / "current.json"

    def _read_json(self, path: Path) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise PublicReleaseUnavailableError() from error

    def _validated(self, path: Path, schema: type[BaseModel]) -> dict[str, Any]:
        try:
            return schema.model_validate(self._read_json(path)).model_dump(mode="json")
        except (ValidationError, TypeError, ValueError) as error:
            raise PublicReleaseUnavailableError() from error

    def current_pointer(self) -> dict[str, Any]:
        return self._validated(self.pointer_path, PublicReleasePointer)

    def release_directory(self) -> Path:
        pointer = self.current_pointer()
        directory = self.town_root / pointer["release_id"]
        if not directory.is_dir():
            raise PublicReleaseUnavailableError()
        return directory

    def _artifact(self, filename: str) -> dict[str, Any]:
        schema = REQUIRED_ARTIFACTS[filename]
        payload = self._validated(self.release_directory() / filename, schema)
        pointer = self.current_pointer()
        if (
            payload.get("town") != pointer["town"]
            or payload.get("source_run_id") != pointer["source_run_id"]
            or payload.get("release_version") != pointer["release_version"]
        ):
            raise PublicReleaseUnavailableError()
        return payload

    def summary(self) -> dict[str, Any]:
        return self._artifact("summary.json")

    def homestead_trend(self) -> dict[str, Any]:
        return self._artifact("homestead-trend.json")

    def providers(self) -> dict[str, Any]:
        return self._artifact("providers.json")

    def map_projection_path(self) -> Path:
        self._artifact("map.geojson")
        return self.release_directory() / "map.geojson"

    def map_projection(self) -> dict[str, Any]:
        return self._artifact("map.geojson")

    def health(self) -> dict[str, str]:
        pointer = self.current_pointer()
        for filename in REQUIRED_ARTIFACTS:
            self._artifact(filename)
        return {
            "status": "ok",
            "town": pointer["town"],
            "release_id": pointer["release_id"],
        }
