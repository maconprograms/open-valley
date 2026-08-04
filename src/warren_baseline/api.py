"""FastAPI endpoints for the evidence-first Warren baseline."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from .repository import BaselineRepository, ReviewLedgerError

DEFAULT_BASELINE_ROOT = Path(__file__).resolve().parents[2] / "warren" / "outputs" / "baseline"


def create_baseline_router(repository: BaselineRepository | None = None) -> APIRouter:
    """Create a router with an injectable repository for isolated tests."""
    repository = repository or BaselineRepository(DEFAULT_BASELINE_ROOT)
    router = APIRouter(prefix="/api/baseline", tags=["Warren baseline"])

    def read(method):
        try:
            return method()
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ReviewLedgerError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @router.get("/summary")
    def summary():
        return read(repository.summary)

    @router.get("/map", response_class=FileResponse)
    def map_projection():
        return read(lambda: FileResponse(repository.map_projection_path(), media_type="application/geo+json"))

    @router.get("/accounts/{account_id}")
    def account_detail(account_id: str):
        return read(lambda: repository.account_detail(account_id))

    @router.get("/transfers")
    def transfers():
        return read(repository.transfer_events)

    @router.get("/trends/homestead")
    def homestead_trend():
        return read(repository.homestead_trend)

    @router.get("/sources")
    def sources():
        return read(repository.sources)

    return router
