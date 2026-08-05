"""Standalone ASGI application for the redacted public release reader."""

from fastapi import FastAPI

from .api import DEFAULT_RELEASES_ROOT, create_baseline_router, create_health_router
from .repository import PublicReleaseRepository


def create_app(repository: PublicReleaseRepository | None = None) -> FastAPI:
    """Build a release-only application with no cross-origin or database setup."""

    repository = repository or PublicReleaseRepository(DEFAULT_RELEASES_ROOT)
    application = FastAPI(
        title="Open Valley public release",
        description="Redacted, evidence-bound Warren release artifacts.",
        version="1.0.0",
    )
    application.include_router(create_baseline_router(repository))
    application.include_router(create_health_router(repository))
    return application


app = create_app()
