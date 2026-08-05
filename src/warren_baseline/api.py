"""FastAPI endpoints for the redacted Open Valley public release."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, TypeVar

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from .repository import PublicReleaseRepository, PublicReleaseUnavailableError

DEFAULT_RELEASES_ROOT = Path(__file__).resolve().parents[2] / "releases"
Result = TypeVar("Result")


def _read_public(method: Callable[[], Result]) -> Result:
    try:
        return method()
    except PublicReleaseUnavailableError as error:
        raise HTTPException(status_code=503, detail="Public release is unavailable.") from error


def create_baseline_router(repository: PublicReleaseRepository | None = None) -> APIRouter:
    """Create the bounded release API router with an injectable reader for tests."""

    repository = repository or PublicReleaseRepository(DEFAULT_RELEASES_ROOT)
    router = APIRouter(prefix="/api/baseline", tags=["Open Valley public release"])

    @router.get("/summary")
    def summary():
        return _read_public(repository.summary)

    @router.get("/map", response_class=FileResponse)
    def map_projection():
        return _read_public(
            lambda: FileResponse(repository.map_projection_path(), media_type="application/geo+json")
        )

    @router.get("/trends/homestead")
    def homestead_trend():
        return _read_public(repository.homestead_trend)

    @router.get("/providers")
    def providers():
        return _read_public(repository.providers)

    return router


def create_health_router(repository: PublicReleaseRepository) -> APIRouter:
    """Create the unprefixed readiness endpoint used by Coolify."""

    router = APIRouter(tags=["service health"])

    @router.get("/healthz")
    def healthz():
        return _read_public(repository.health)

    return router
