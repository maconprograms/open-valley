"""FastAPI application for Warren Community Intelligence."""

import logging
import os
from contextlib import asynccontextmanager

import logfire
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request

from .agent import WarrenContext, warren_agent
from .database import init_db

logger = logging.getLogger(__name__)

# Configure Logfire for observability
if os.getenv("LOGFIRE_TOKEN"):
    logfire.configure()
    logfire.instrument_fastapi()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db()
    yield


app = FastAPI(
    title="Open Valley API",
    description="Warren Community Intelligence - AI agent for exploring community data",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Open Valley API"}


@app.get("/llms.txt")
async def llms_txt():
    """Documentation for AI agents about this API."""
    return """# Open Valley API

## Overview
Open Valley is a community data platform for Warren, Vermont.
It provides property data, residency patterns, and community statistics
through a conversational AI interface with live visualizations.

## Data Available
- Parcels: 1,823 properties with addresses, assessed values, acreage, coordinates
- Owners: Property ownership information with mailing addresses
- Tax Status: Homestead exemption filings (indicates primary residence)
- Total Assessed Value: ~$496 million

## Key Concepts
- SPAN: Vermont's unique parcel identifier (e.g., 690-219-11993)
- Homestead: Primary residence filing - if filed, likely year-round resident
- Assessed Value: Town's valuation for tax purposes

## Warren, VT Context
Warren is a small town in the Mad River Valley with ~1,800 residents.
It's home to Sugarbush Resort and has a significant second-home population.
About 76% of properties have NOT filed homestead exemptions (likely second homes).

## Agent Tools
The Warren Property Assistant has these capabilities:
- get_property_stats() - Aggregate statistics (count, values, homestead %)
- get_property_type_breakdown() - Properties by type (residential, commercial, etc.)
- search_properties(...) - Search by address, owner, value, homestead status
- get_property_by_span(span) - Get specific property by SPAN ID

## API Endpoints
- GET / - Health check
- GET /llms.txt - This documentation
- POST /awp - AG-UI streaming endpoint for chat interactions
"""


@app.get("/awp/info")
async def awp_info():
    """AG-UI info endpoint - returns available agents for CopilotKit discovery."""
    return {
        "agents": {
            "default": {
                "name": "default",
                "description": "Warren Property Assistant - helps explore property data in Warren, VT"
            }
        },
        "actions": [],
        "version": "1.0"
    }


@app.post("/awp/info")
async def awp_info_post():
    """AG-UI info endpoint (POST) - same as GET for CopilotKit compatibility."""
    return {
        "agents": {
            "default": {
                "name": "default",
                "description": "Warren Property Assistant - helps explore property data in Warren, VT"
            }
        },
        "actions": [],
        "version": "1.0"
    }


@app.post("/awp")
async def awp_endpoint(request: Request):
    """CopilotKit-compatible AG-UI endpoint.

    Handles the JSON-RPC style protocol used by CopilotKit and dispatches
    to Pydantic AI's AGUIAdapter for streaming responses.
    """
    import json
    from fastapi.responses import JSONResponse

    body_bytes = await request.body()
    body = json.loads(body_bytes.decode())
    method = body.get("method", "")

    logger.debug(f"AWP Request method: {method}")

    # Handle CopilotKit's JSON-RPC style protocol
    if method == "info":
        return JSONResponse({
            "agents": {
                "default": {
                    "name": "default",
                    "description": "Warren Property Assistant - helps explore property data in Warren, VT"
                }
            },
            "actions": [],
            "version": "1.0"
        })

    if method in ("agent/connect", "agent/run"):
        # Extract the AG-UI payload from body.body
        ag_ui_payload = body.get("body", {})
        logger.debug(f"AG-UI payload ({method}): {json.dumps(ag_ui_payload)[:200]}...")

        # Convert to AG-UI format and dispatch via Pydantic AI
        from pydantic_ai.ui.ag_ui import AGUIAdapter
        from starlette.requests import Request as StarletteRequest

        # Reconstruct request with just the AG-UI payload
        ag_ui_body = json.dumps(ag_ui_payload).encode()
        scope = request.scope.copy()

        async def receive():
            return {"type": "http.request", "body": ag_ui_body}

        new_request = StarletteRequest(scope, receive)

        try:
            response = await AGUIAdapter.dispatch_request(
                new_request,
                agent=warren_agent,
                deps=WarrenContext(),
            )
            return response
        except Exception as e:
            logger.exception(f"AGUIAdapter error: {e}")
            raise

    # Unknown method
    return JSONResponse({"error": f"Unknown method: {method}"}, status_code=400)
