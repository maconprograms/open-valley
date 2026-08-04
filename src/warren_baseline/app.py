"""Standalone ASGI app for the Warren evidence-first baseline."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import create_baseline_router

app = FastAPI(
    title="Open Valley — Warren baseline",
    description="Evidence-first Warren property, homestead, mailing, and transfer facts.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3999"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(create_baseline_router())


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "service": "Open Valley Warren baseline"}
