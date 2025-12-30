# Open Valley - Warren Community Intelligence

A conversational AI platform for exploring Warren, VT community data through a Pydantic AI agent with live visualizations.

## Project Status

**Phase 1: Complete** - Database + Agent
- PostgreSQL + PostGIS running in Docker
- SQLAlchemy models for Parcels, Owners, TaxStatus
- 1,823 Warren parcels imported from Vermont Geodata
- Pydantic AI agent with 4 tools (Claude Opus 4.5 via Gateway)
- Logfire observability configured

**Phase 2: Complete** - AG-UI Streaming + Visualizations
- FastAPI `/awp` endpoint with CopilotKit-compatible AG-UI protocol
- Next.js frontend with CopilotChat integration
- Artifact system with auto-generation from tool results
- Working visualizations: Stats cards, Pie charts, Data tables
- Artifact carousel for navigation

**Phase 3: Complete** - Front Porch Forum Import
- 3,298 daily digests imported (58,174 posts, 6,438 unique people)
- SQLAlchemy models: FPFIssue, FPFPerson, FPFPost, Organization
- BeautifulSoup parser for extracting posts from HTML emails
- Person deduplication by email or (name + road + town)

## Quick Start

```bash
# 1. Start PostgreSQL database
docker compose up -d

# 2. Run API server (in one terminal)
cd api
uv sync
uv run uvicorn src.main:app --reload --port 8000

# 3. Run frontend (in another terminal)
cd web
npm install
npm run dev
```

Open http://localhost:3000 to use the chat interface.

## Database Access

**Docker PostgreSQL:**
```
Host: localhost
Port: 5432
Database: openvalley
Username: openvalley
Password: openvalley
```

**Connection string:**
```
postgresql://openvalley:openvalley@localhost:5432/openvalley
```

**Connect via psql:**
```bash
docker compose exec db psql -U openvalley -d openvalley
```

**Useful queries:**
```sql
-- Count all parcels
SELECT COUNT(*) FROM parcels;

-- Property statistics
SELECT
  COUNT(*) as total,
  SUM(assessed_total) as total_value,
  AVG(assessed_total) as avg_value
FROM parcels;

-- Homestead breakdown
SELECT
  homestead_filed,
  COUNT(*) as count
FROM tax_status
GROUP BY homestead_filed;

-- Search properties by address
SELECT p.span, p.address, p.assessed_total, o.name as owner
FROM parcels p
LEFT JOIN owners o ON o.parcel_id = p.id
WHERE p.address ILIKE '%MAIN%'
LIMIT 10;
```

## Project Structure

```
open-valley/
├── api/                      # Python backend
│   ├── src/
│   │   ├── agent.py          # Pydantic AI agent with tools
│   │   ├── database.py       # SQLAlchemy engine/session
│   │   ├── main.py           # FastAPI application + AG-UI endpoint
│   │   └── models.py         # SQLAlchemy ORM models
│   ├── scripts/
│   │   ├── import_parcels.py   # Vermont Geodata parcel import
│   │   └── parse_fpf_emails.py # Front Porch Forum email import
│   └── pyproject.toml
├── web/                      # Next.js frontend
│   ├── src/
│   │   ├── app/
│   │   │   └── page.tsx      # Main chat + artifacts UI
│   │   └── components/
│   │       ├── ArtifactPanel.tsx
│   │       └── artifacts/    # Visualization components
│   └── package.json
├── docker-compose.yml        # PostgreSQL + PostGIS
└── CLAUDE.md                 # This file
```

## Architecture

- **Agent**: Pydantic AI with Claude Opus 4.5 via Pydantic AI Gateway
- **Protocol**: AG-UI streaming over CopilotKit's JSON-RPC wrapper
- **Database**: PostgreSQL with PostGIS (Docker locally)
- **ORM**: SQLAlchemy 2.0 with typed models
- **API**: FastAPI with CORS for frontend
- **Frontend**: Next.js 14 + CopilotKit + Recharts + Leaflet
- **Observability**: Logfire (optional, via LOGFIRE_TOKEN)

## Agent Tools

The Warren Property Assistant has these tools defined in `api/src/agent.py`:

| Tool | Returns | Description |
|------|---------|-------------|
| `get_property_stats()` | PropertyStats | Aggregate stats: count, total value, homestead % |
| `get_property_type_breakdown()` | list[PropertyTypeBreakdown] | Properties grouped by type |
| `search_properties(...)` | list[PropertySummary] | Search by address, owner, value, homestead |
| `get_property_by_span(span)` | PropertySummary | Single property by SPAN ID |

## Artifact Types

Tool results automatically generate visualizations:

| Tool Result | Artifacts Generated |
|-------------|---------------------|
| `get_property_stats` | Stats cards + Pie chart |
| `search_properties` | Map (if coords) + Data table |
| `get_property_type_breakdown` | Bar chart + Table |
| `get_property_by_span` | Property card + Map |

## Environment Variables

Create `api/.env`:
```
DATABASE_URL=postgresql://openvalley:openvalley@localhost:5432/openvalley
PYDANTIC_AI_GATEWAY_API_KEY=<your-gateway-key>
LOGFIRE_TOKEN=<optional-logfire-token>
```

## Data Model

### Property Tables
- **parcels**: 1,823 properties with SPAN, address, assessed values, lat/lng, geometry
- **owners**: Property ownership with mailing addresses
- **tax_status**: Homestead exemption filings (indicates primary residence)

### Front Porch Forum Tables
- **fpf_issues**: 3,298 daily email digests (issue_number, published_at, gmail_id, subject)
- **fpf_people**: 6,438 community members (name, email, road, town, first/last_seen_at)
- **fpf_posts**: 58,174 posts (title, content, category, is_reply, linked to issue + person)
- **organizations**: Placeholder for orgs mentioned in posts (to be populated via NER)

### Key Insights
- ~76% of Warren properties have NOT filed homestead exemptions (likely second homes)
- Top FPF towns: Warren (2,459 people), Waitsfield (2,401), Fayston (944), Moretown (202)
- Most active categories: Announcements, For sale, Free items, Seeking items

## Development Commands

```bash
# Database
docker compose up -d          # Start PostgreSQL
docker compose down           # Stop PostgreSQL
docker compose logs -f db     # View database logs

# Python API
cd api
uv sync                       # Install dependencies
uv run uvicorn src.main:app --reload  # Run dev server
uv run python -m src.agent    # Test agent directly

# Frontend
cd web
npm install                   # Install dependencies
npm run dev                   # Run dev server (port 3000)

# Import parcel data (first time only)
cd api
uv run python scripts/import_parcels.py --import

# Import FPF emails (requires data/fpf_emails/*.json)
uv run python scripts/parse_fpf_emails.py
```

## Data Sources

- **Vermont Geodata Portal**: ArcGIS REST API for parcel boundaries and Grand List data
- **API Endpoint**: `FS_VCGI_OPENDATA_Cadastral_VTPARCELS_poly_standardized_parcels_SP_v1`
- **Town**: Warren (filtered by TOWN = 'WARREN')

- **Front Porch Forum**: Daily email digests for Mad River Valley communities
- **Coverage**: Warren, Waitsfield, Fayston, Moretown, Duxbury, Granville
- **Data**: 3,299 emails exported from Gmail → `data/fpf_emails/*.json`
