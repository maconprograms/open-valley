# Open Valley - Warren Community Intelligence

Understanding our community through data, starting with land and dwellings.

## Purpose

Warren, VT faces a housing challenge: only ~20% of dwellings are primary residences. The rest are second homes (70%) and short-term rentals (10%). This project opens up community data to help residents, policymakers, and the Planning Commission understand residency patterns and trends.

**Core Question**: Who lives here, who owns what, and how is our housing being used?

## Key Concepts

This project uses terminology from Vermont Act 73 (2025). See `docs/GLOSSARY.md` for complete definitions.

### Parcel → Dwelling → Classification

**Parcel**: A discrete piece of land identified by SPAN. Warren has 1,823 parcels with various "highest and best uses" (residential, farm, commercial, woodland, seasonal).

**Dwelling**: A subset of parcels where the highest/best use is year-round housing. Per Act 73:
> A building or part of a building with separate entrance, designed for occupancy by one or more persons, providing living facilities for sleeping, cooking, and sanitary needs, and fit for year-round habitation.

Warren has 2,175 dwellings across 1,823 parcels (some parcels have multiple units).

### Act 73 Tax Classifications (Vermont 2025)
- **HOMESTEAD**: Owner's domicile 6+ months/year
- **NHS_RESIDENTIAL**: Second homes, STRs, vacant year-round (higher rate)
- **NHS_NONRESIDENTIAL**: Long-term rentals, 5+ units, commercial (highest rate)

### Data Hierarchy
```
Parcel (1,823) → Dwelling (2,175) → STR Listing (605)
                      ↓
                   Person ← PropertyOwnership
                      ↓
                Organization (LLCs, trusts, boards)
```

### Medallion Architecture
- **Bronze**: Raw API data (`bronze_pttr_transfers`, `bronze_str_listings`)
- **Silver**: Validated, linked to parcels (`property_transfers`, `str_listings`, `dwellings`)
- **Gold**: Aggregated analytics (views, materialized tables)

## Project Structure

```
open-valley/
├── api/src/
│   ├── agent.py      # Pydantic AI agent with tools
│   ├── models.py     # SQLAlchemy models (Person, Dwelling, etc.)
│   ├── schemas.py    # Pydantic validation with Act 73 rules
│   └── main.py       # FastAPI + AG-UI endpoint
├── web/src/
│   └── app/page.tsx  # Chat + artifact visualization
├── docs/
│   ├── DATA_ARCHITECTURE.md    # Full entity design
│   ├── CALIBRATION_PROPERTIES.md  # Ground truth test cases
│   └── DWELLING_DATA_ARCHITECTURE.md
└── scripts/          # Import pipelines
```

## Documentation Pointers

| Topic | Location |
|-------|----------|
| **Act 73 terminology & glossary** | `docs/GLOSSARY.md` |
| Data sources & APIs | `DATA_SOURCES.md` |
| Entity relationships | `docs/DATA_ARCHITECTURE.md` |
| STR matching & confidence | `docs/STR_DATA_CONFIDENCE.md` |
| Act 73 classification logic | `src/schemas.py` (TaxClassification, DwellingBase) |
| Dwelling inference | `scripts/infer_dwellings.py` |
| Ground truth properties | `docs/CALIBRATION_PROPERTIES.md` |
| Agent tools | `src/agent.py` |

## Database

```
postgresql://openvalley:openvalley@localhost:5432/openvalley
```

Connect: `docker compose exec db psql -U openvalley -d openvalley`

## Environment Variables

Create `api/.env`:
```
DATABASE_URL=postgresql://openvalley:openvalley@localhost:5432/openvalley
PYDANTIC_AI_GATEWAY_API_KEY=<gateway-key>
OPENAI_API_KEY=<openai-key>
```

## Common Tasks

```bash
# Import/refresh parcel data
uv run python scripts/import_parcels.py --import

# Import STR listings from AirROI
uv run python scripts/import_airroi.py --all --city Warren

# Infer dwellings from parcels + STR + tax data
uv run python scripts/infer_dwellings.py

# Import property transfers
uv run python scripts/import_pttr.py --all
```

## Key Data Insights

- **2,175 dwellings** in Warren (from 1,823 parcels)
- **431 (20%)** are primary residences (HOMESTEAD)
- **1,744 (80%)** are non-homestead (second homes + STRs)
- **605 STR listings** matched to parcels (96% match rate)
- **~64% of buyers** are out-of-state (PTTR data)

## Guardrails

1. **DESCPROP over CAT**: Grand List `CAT` codes are unreliable for dwelling count. Parse `DESCPROP` field instead ("& DWL" = 1, "& 2 DWLS" = 2).

2. **LLCs can't homestead**: If owner name contains "LLC", "TRUST", "INC" → cannot file homestead declaration.

3. **Calibration properties**: Test changes against Woods Road properties in `docs/CALIBRATION_PROPERTIES.md`.

4. **Schema Engineering**: Put business rules in Pydantic Field descriptions, not prose. See `api/src/schemas.py`.
