"""FastAPI application for Warren Community Intelligence."""

import logging
import os
from contextlib import asynccontextmanager

import logfire
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import func
from starlette.requests import Request

import httpx

from .agent import WarrenContext, warren_agent
from .database import SessionLocal, init_db
from .models import Dwelling, Parcel, STRListing, TaxStatus

# Vermont Geodata ArcGIS REST API
ARCGIS_BASE = "https://services1.arcgis.com/BkFxaEFNwHqX3tAw/arcgis/rest/services"
PARCELS_LAYER = "FS_VCGI_OPENDATA_Cadastral_VTPARCELS_poly_standardized_parcels_SP_v1/FeatureServer/0"
PARCELS_URL = f"{ARCGIS_BASE}/{PARCELS_LAYER}/query"

logger = logging.getLogger(__name__)


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

# Configure Logfire for observability (after app creation)
if os.getenv("LOGFIRE_TOKEN"):
    logfire.configure()
    logfire.instrument_fastapi(app)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3999", "http://localhost:5173"],
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
                "description": "Warren Property Assistant - helps explore property data in Warren, VT",
            }
        },
        "actions": [],
        "version": "1.0",
    }


@app.post("/awp/info")
async def awp_info_post():
    """AG-UI info endpoint (POST) - same as GET for CopilotKit compatibility."""
    return {
        "agents": {
            "default": {
                "name": "default",
                "description": "Warren Property Assistant - helps explore property data in Warren, VT",
            }
        },
        "actions": [],
        "version": "1.0",
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
        return JSONResponse(
            {
                "agents": {
                    "default": {
                        "name": "default",
                        "description": "Warren Property Assistant - helps explore property data in Warren, VT",
                    }
                },
                "actions": [],
                "version": "1.0",
            }
        )

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


# =============================================================================
# Dashboard Stats API
# =============================================================================


class ParcelStats(BaseModel):
    """Statistics about parcels."""
    count: int
    total_value: int


class HomesteadStats(BaseModel):
    """Homestead statistics."""
    count: int
    percent: float


class DwellingStats(BaseModel):
    """Dwelling statistics by classification."""
    total: int
    homestead: HomesteadStats
    nhs_residential: HomesteadStats


class STRStats(BaseModel):
    """Short-term rental statistics."""
    count: int


class DashboardStatsResponse(BaseModel):
    """Complete dashboard statistics response."""
    parcels: ParcelStats
    dwellings: DwellingStats
    str_listings: STRStats


@app.get("/api/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats():
    """Return key statistics for the dashboard.

    This endpoint provides aggregate statistics for the Open Valley dashboard:
    - Total parcels and assessed value
    - Dwelling breakdown by Act 73 classification (homestead vs NHS residential)
    - Short-term rental listing count
    """
    db = SessionLocal()
    try:
        # Parcel statistics
        parcel_count = db.query(func.count(Parcel.id)).scalar() or 0
        total_value = db.query(func.sum(Parcel.assessed_total)).scalar() or 0

        # Dwelling statistics (Act 73 classifications)
        total_dwellings = db.query(func.count(Dwelling.id)).scalar() or 0
        homestead_dwellings = db.query(func.count(Dwelling.id)).filter(
            Dwelling.tax_classification == "HOMESTEAD"
        ).scalar() or 0
        nhs_residential_dwellings = db.query(func.count(Dwelling.id)).filter(
            Dwelling.tax_classification == "NHS_RESIDENTIAL"
        ).scalar() or 0

        # Calculate percentages (avoid division by zero)
        if total_dwellings > 0:
            homestead_pct = round((homestead_dwellings / total_dwellings) * 100, 1)
            nhs_pct = round((nhs_residential_dwellings / total_dwellings) * 100, 1)
        else:
            # Fallback to parcel-based homestead calculation if no dwellings
            homestead_count = db.query(func.count(TaxStatus.id)).filter(
                TaxStatus.homestead_filed == True
            ).scalar() or 0
            non_homestead_count = db.query(func.count(TaxStatus.id)).filter(
                TaxStatus.homestead_filed == False
            ).scalar() or 0
            total_with_status = homestead_count + non_homestead_count

            if total_with_status > 0:
                homestead_pct = round((homestead_count / total_with_status) * 100, 1)
                nhs_pct = round((non_homestead_count / total_with_status) * 100, 1)
                homestead_dwellings = homestead_count
                nhs_residential_dwellings = non_homestead_count
                total_dwellings = total_with_status
            else:
                homestead_pct = 0.0
                nhs_pct = 0.0

        # STR listing count
        str_count = db.query(func.count(STRListing.id)).filter(
            STRListing.is_active == True
        ).scalar() or 0

        return DashboardStatsResponse(
            parcels=ParcelStats(
                count=parcel_count,
                total_value=int(total_value),
            ),
            dwellings=DwellingStats(
                total=total_dwellings,
                homestead=HomesteadStats(
                    count=homestead_dwellings,
                    percent=homestead_pct,
                ),
                nhs_residential=HomesteadStats(
                    count=nhs_residential_dwellings,
                    percent=nhs_pct,
                ),
            ),
            str_listings=STRStats(count=str_count),
        )
    finally:
        db.close()


# =============================================================================
# GeoJSON API for MapLibre
# =============================================================================

# Cache for Vermont Geodata response (avoid repeated API calls)
_geojson_cache: dict = {"data": None, "timestamp": 0}
CACHE_TTL = 3600  # 1 hour


@app.get("/api/parcels/geojson")
async def get_parcels_geojson():
    """Return Warren parcels as GeoJSON with homestead classification.

    Fetches geometry from Vermont Geodata API and enriches with local
    homestead filing status for choropleth visualization.
    """
    import time

    current_time = time.time()

    # Check cache
    if _geojson_cache["data"] and (current_time - _geojson_cache["timestamp"]) < CACHE_TTL:
        logger.debug("Returning cached GeoJSON")
        return _geojson_cache["data"]

    # Fetch from Vermont Geodata
    logger.info("Fetching parcels from Vermont Geodata API...")

    all_features = []
    offset = 0

    async with httpx.AsyncClient(timeout=60.0) as client:
        while True:
            params = {
                "where": "TOWN = 'WARREN'",
                "outFields": "SPAN,E911ADDR,OWNER1,REAL_FLV,ACRESGL,HSDECL",
                "returnGeometry": "true",
                "outSR": "4326",
                "f": "geojson",
                "resultOffset": offset,
                "resultRecordCount": 1000,
            }

            response = await client.get(PARCELS_URL, params=params)
            response.raise_for_status()
            data = response.json()

            features = data.get("features", [])
            if not features:
                break

            all_features.extend(features)

            if len(features) < 1000:
                break
            offset += 1000

    logger.info(f"Fetched {len(all_features)} parcels from Vermont Geodata")

    # Get local homestead data for enrichment
    db = SessionLocal()
    try:
        # Build SPAN -> homestead_filed lookup
        tax_records = db.query(TaxStatus.parcel_id, TaxStatus.homestead_filed, Parcel.span).join(
            Parcel, TaxStatus.parcel_id == Parcel.id
        ).all()

        homestead_lookup = {r.span: r.homestead_filed for r in tax_records}
        logger.debug(f"Built homestead lookup with {len(homestead_lookup)} entries")
    finally:
        db.close()

    # Enrich features with local homestead data
    for feature in all_features:
        props = feature.get("properties", {})
        span = props.get("SPAN")

        # Use local data if available, otherwise fall back to API data
        if span and span in homestead_lookup:
            props["homestead_filed"] = homestead_lookup[span]
        else:
            # Fall back to HSDECL from API
            props["homestead_filed"] = props.get("HSDECL") == "Y"

        # Add classification for choropleth
        props["classification"] = "homestead" if props["homestead_filed"] else "second_home"

    result = {
        "type": "FeatureCollection",
        "features": all_features,
    }

    # Update cache
    _geojson_cache["data"] = result
    _geojson_cache["timestamp"] = current_time

    return result


# =============================================================================
# Homestead Transitions API (for animated map)
# =============================================================================


@app.get("/api/transfers/transitions")
async def get_homestead_transitions():
    """Return homestead transitions as GeoJSON for map animation.

    Each feature represents a property transfer classified by actual status change:

    - TRUE_LOSS: VT seller (was homestead) → non-primary buyer (de-homesteading)
    - TRUE_GAIN: Non-VT seller (was 2nd home) → primary buyer (re-homesteading)
    - STAYED_HOMESTEAD: VT seller → primary buyer (no net change)
    - STAYED_NON_HOMESTEAD: Non-VT seller → non-primary buyer (no net change)
    - OTHER: Unknown seller state, open land, commercial, etc.

    Uses coordinates directly from PTTR data (93% coverage).
    """
    from sqlalchemy import text as sql_text

    db = SessionLocal()
    try:
        result = db.execute(sql_text("""
            SELECT
                b.raw_json::json->'attributes'->>'span' as span,
                (b.raw_json::json->'attributes'->>'Latitude')::float as lat,
                (b.raw_json::json->'attributes'->>'Longitude')::float as lng,
                pt.transfer_date,
                pt.sale_price,
                b.raw_json::json->'attributes'->>'sellerSt' as seller_state,
                b.raw_json::json->'attributes'->>'bUsePrDesc' as use_desc,
                pt.buyer_state,
                CASE
                    -- TRUE LOSS: VT seller (was homestead) → non-primary buyer
                    WHEN b.raw_json::json->'attributes'->>'sellerSt' = 'VT'
                         AND (pt.intended_use = 'secondary'
                              OR b.raw_json::json->'attributes'->>'bUsePrDesc' LIKE 'Non-PR%')
                    THEN 'TRUE_LOSS'

                    -- TRUE GAIN: Non-VT seller (was 2nd home) → primary buyer
                    WHEN b.raw_json::json->'attributes'->>'sellerSt' IS NOT NULL
                         AND b.raw_json::json->'attributes'->>'sellerSt' != 'VT'
                         AND b.raw_json::json->'attributes'->>'bUsePrDesc'
                             IN ('Domicile/Primary Residence', 'Principal Residence')
                    THEN 'TRUE_GAIN'

                    -- STAYED HOMESTEAD: VT seller → primary buyer (no change)
                    WHEN b.raw_json::json->'attributes'->>'sellerSt' = 'VT'
                         AND b.raw_json::json->'attributes'->>'bUsePrDesc'
                             IN ('Domicile/Primary Residence', 'Principal Residence')
                    THEN 'STAYED_HOMESTEAD'

                    -- STAYED NON-HOMESTEAD: Non-VT seller → non-primary buyer (no change)
                    WHEN b.raw_json::json->'attributes'->>'sellerSt' IS NOT NULL
                         AND b.raw_json::json->'attributes'->>'sellerSt' != 'VT'
                         AND (pt.intended_use = 'secondary'
                              OR b.raw_json::json->'attributes'->>'bUsePrDesc' LIKE 'Non-PR%')
                    THEN 'STAYED_NON_HOMESTEAD'

                    -- OTHER: Unknown seller state, open land, commercial, etc.
                    ELSE 'OTHER'
                END as transition_type
            FROM property_transfers pt
            JOIN bronze_pttr_transfers b ON pt.bronze_id = b.id
            WHERE pt.transfer_date >= '2019-01-01'
              AND (b.raw_json::json->'attributes'->>'Latitude')::float != 0
              AND (b.raw_json::json->'attributes'->>'Longitude')::float != 0
            ORDER BY pt.transfer_date
        """))

        features = []
        for row in result:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(row.lng), float(row.lat)]
                },
                "properties": {
                    "span": row.span,
                    "date": row.transfer_date.isoformat() if row.transfer_date else None,
                    "year": row.transfer_date.year if row.transfer_date else None,
                    "sale_price": row.sale_price,
                    "seller_state": row.seller_state,
                    "buyer_state": row.buyer_state,
                    "use_desc": row.use_desc,
                    "transition_type": row.transition_type,
                }
            })

        # Calculate summary stats by year with new categories
        stats_result = db.execute(sql_text("""
            SELECT
                EXTRACT(YEAR FROM pt.transfer_date)::int as year,
                -- TRUE LOSS: VT seller → non-primary (de-homesteading)
                COUNT(*) FILTER (WHERE
                    b.raw_json::json->'attributes'->>'sellerSt' = 'VT'
                    AND (pt.intended_use = 'secondary'
                         OR b.raw_json::json->'attributes'->>'bUsePrDesc' LIKE 'Non-PR%')
                ) as true_losses,
                -- TRUE GAIN: Non-VT seller → primary (re-homesteading)
                COUNT(*) FILTER (WHERE
                    b.raw_json::json->'attributes'->>'sellerSt' IS NOT NULL
                    AND b.raw_json::json->'attributes'->>'sellerSt' != 'VT'
                    AND b.raw_json::json->'attributes'->>'bUsePrDesc'
                        IN ('Domicile/Primary Residence', 'Principal Residence')
                ) as true_gains,
                -- STAYED HOMESTEAD: VT seller → primary (no change)
                COUNT(*) FILTER (WHERE
                    b.raw_json::json->'attributes'->>'sellerSt' = 'VT'
                    AND b.raw_json::json->'attributes'->>'bUsePrDesc'
                        IN ('Domicile/Primary Residence', 'Principal Residence')
                ) as stayed_homestead,
                -- STAYED NON-HOMESTEAD: Non-VT seller → non-primary (no change)
                COUNT(*) FILTER (WHERE
                    b.raw_json::json->'attributes'->>'sellerSt' IS NOT NULL
                    AND b.raw_json::json->'attributes'->>'sellerSt' != 'VT'
                    AND (pt.intended_use = 'secondary'
                         OR b.raw_json::json->'attributes'->>'bUsePrDesc' LIKE 'Non-PR%')
                ) as stayed_non_homestead
            FROM property_transfers pt
            JOIN bronze_pttr_transfers b ON pt.bronze_id = b.id
            WHERE pt.transfer_date >= '2019-01-01'
              AND (b.raw_json::json->'attributes'->>'Latitude')::float != 0
              AND (b.raw_json::json->'attributes'->>'Longitude')::float != 0
            GROUP BY 1
            ORDER BY 1
        """))

        yearly_stats = {
            row.year: {
                "true_losses": row.true_losses,
                "true_gains": row.true_gains,
                "stayed_homestead": row.stayed_homestead,
                "stayed_non_homestead": row.stayed_non_homestead,
                "net": row.true_gains - row.true_losses,
            }
            for row in stats_result
        }

        # Count by transition type
        true_gains = sum(1 for f in features if f["properties"]["transition_type"] == "TRUE_GAIN")
        true_losses = sum(1 for f in features if f["properties"]["transition_type"] == "TRUE_LOSS")
        stayed_homestead = sum(1 for f in features if f["properties"]["transition_type"] == "STAYED_HOMESTEAD")
        stayed_non_homestead = sum(1 for f in features if f["properties"]["transition_type"] == "STAYED_NON_HOMESTEAD")
        other = sum(1 for f in features if f["properties"]["transition_type"] == "OTHER")

        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "total_features": len(features),
                "true_gains": true_gains,
                "true_losses": true_losses,
                "stayed_homestead": stayed_homestead,
                "stayed_non_homestead": stayed_non_homestead,
                "other": other,
                "net_change": true_gains - true_losses,
                "yearly_stats": yearly_stats,
            }
        }
    finally:
        db.close()
