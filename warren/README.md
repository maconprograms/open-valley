# Warren, VT

Complete property/CAMA assessment database for Warren, VT (from the town's public
NEMRC portal), joined to the **VCGI statewide parcel GIS** for geometry and map
coordinates.

- **Properties:** 3,105 (every parcel in the NEMRC database)
- **Parcel polygons:** 3,245 (VCGI), 96% joined to the assessment data
- **NEMRC source updated:** 2026-05-15 · **Built:** 2026-05-31

## Outputs (`warren/outputs/`)

| File | Rows | What it is |
|------|------|------------|
| `warren_joined.csv` | 3,105 | **Start here.** Assessment data + GIS extras (E911 address, grand-list values, and a **lon/lat centroid** for mapping). One row per parcel. |
| `warren_properties.csv` | 3,105 | Assessment-only main table: owner, location, mailing block, SPAN, acres, status, last sale, all assessed values. |
| `warren_buildings.csv` | 3,153 | One row per building/improvement (year built, style, beds/baths, SF…). Join on `parcel_id` + `building_no`. |
| `warren_land.csv` | 2,430 | One row per land segment. Join on `parcel_id` + `land_no`. |
| `warren_parcels.geojson` | 3,245 | **Parcel boundary polygons** (WGS84) + all 56 VCGI fields. Open in QGIS / geojson.io / Leaflet. |
| `warren_parcels_gis.csv` | 3,245 | VCGI attribute table (no geometry). Keyed by SPAN/PARCID. |
| `warren_properties.json` | 3,105 | Full nested record per parcel — every field from the property card. |
| `parcels.txt` | 3,105 | List of all parcel IDs. |

## Evidence-first baseline dashboard

`warren/outputs/baseline/` is the canonical input for the new Warren baseline
API and map. It is an append-only set of source runs rather than a replacement
for the source extracts above. `manifest.json` identifies the validated,
promoted `current_run`; each run preserves JSONL observations, its source
checksums, coverage, and a privacy-preserving `map-tax-status-v1.geojson`
projection.

The dashboard deliberately shows separate denominators:

| Measure | Denominator | Meaning | It does **not** establish |
|---|---|---|---|
| Tax accounts | Current NEMRC property-account rows | Current account inventory | Housing units or occupied homes |
| Housing-unit claims | Source-supported claims attached to accounts | Documented, inferred, and unknown physical-unit evidence | An official unit inventory or occupancy |
| Homestead filed | Accounts with a known VCGI `HSDECL` flag | A filed homestead declaration | A full-time resident |
| PTTR transfers | State transfer-event rows | A recorded sale/transfer event | A homestead gain/loss without dated before-and-after evidence |

### Refreshing the current baseline

Run this from the repository root after refreshing the NEMRC and VCGI extracts.
The PTTR fetch is the Vermont state ArcGIS source; it is intentionally stored as
a dated, reproducible input to the source run.

```bash
uv run python warren/scripts/join_nemrc_vcgi.py
uv run python warren/scripts/fetch_pttr_baseline.py
uv run python -m warren.scripts.build_baseline --pttr warren/outputs/warren_pttr.json
uv run python -c "from pathlib import Path; from src.warren_baseline.repository import BaselineRepository; r = BaselineRepository(Path('warren/outputs/baseline')); r.promote(r.manifest()['last_staged_run'])"
```

Promotion only moves the manifest pointer after a run has been validated and its
local map projection has been created. It does not overwrite past source runs.
The standalone baseline API routes are `/api/baseline/summary`, `/map`,
`/accounts/{account_id}`, `/transfers`, and `/sources`. Start it without the
legacy database or AI services with:

```bash
uv run uvicorn src.warren_baseline.app:app --port 8998
```

For the browser dashboard, start Next.js from `web/` with `npm run dev -- -p
3999` and open `http://localhost:3999/`. Its same-origin `/api/baseline/*`
requests are proxied to the standalone API. The public map exposes only the
tax-status buckets `homestead_filed`, `non_homestead`, and `unknown`, plus
address, GIS-link, and unit-evidence fields. It does not expose owner or
mailing fields. A homestead filing remains a source fact, not an occupancy or
second-home classification. See `warren/reviews/` for the separate local
human-review ledger.

### Historical homestead series

The VCGI archive retains Grand List snapshots, including the source `HSDECL`
field. The large statewide archive ZIPs are re-fetchable local inputs in
`warren/raw_vcgi_snapshots/` (ignored by Git); the committed Warren-only output
is `warren/outputs/historical/`. Rebuild it with:

```bash
uv run python warren/scripts/extract_historical_homesteads.py
```

The resulting annual metric is **homestead filed among Grand List records with
`PARCID`**, not a housing-unit or residency rate. The 2017 archive is retained
as a documented coverage gap because it has no usable Warren Grand List join;
the first usable year is 2018.

The extraction also includes a sensitivity that excludes `CAT=O` (or legacy
`CAT=Other`) records. In the current source, 1,304 of 1,305 `O` records share a
`C-` SPAN, the VCGI condominium/common-area grouping; this makes the category a
useful resort/condo-density proxy. It remains a proxy: the dashboard labels the
exclusion rather than asserting every `O` record is a condominium or that all
other records are low-density homes.

For this first town, the append-only source files are the right storage layer:
they preserve raw archive provenance, are reviewable without a database, and
keep the time series reproducible. Add Postgres once we need cross-town queries,
review workflows, or interactive joins across many annual account snapshots;
the ledger records map directly to future relational tables.

## Keys & how the tables relate

- **`parcel_id`** links the NEMRC tables (`properties`, `buildings`, `land`, `joined`).
- **GIS join:** `warren_joined.csv` matches NEMRC `parcel_id` to the VCGI parcel's
  cleaned `PARCID` (97% direct), falling back to `SPAN`. Result: **3,003 of 3,105
  parcels (96%) carry a `gis_lon`/`gis_lat`** and the GIS columns (`gis_*`).
  The 102 unmatched are mostly retired/exempt parcels or ones VCGI hasn't mapped;
  `gis_match=none` flags them.
- **SPAN** (Vermont's statewide parcel ID) is present in both datasets but is *not*
  unique in VCGI — condos share one building SPAN across many units — so PARCID is
  the better join key.

## Pipeline (`warren/scripts/`)

Stdlib-only Python (no external packages). Re-runnable as `fetch → parse → join`:

```bash
cd warren/scripts

# 1. parcel list + summary (empty NEMRC search = all records):
curl -s "https://nemrc.info/web_data/vtwarr/resultsT.php" \
  --data "parcelID=&ownerName=&parcelStreetNum=&parcelLocation=&siteName=Warren&siteCode=vtwarr&tableName=VTWARRCAMA&module=ca&searchFldCount=4" \
  -o ../outputs/_all_records_summary.html
grep -oE "camadetailT\.php\?prop=[0-9A-Za-z]+" ../outputs/_all_records_summary.html \
  | sed 's/.*prop=//' | sort -u > ../outputs/parcels.txt

# 2. NEMRC assessment data
bash fetch_all.sh          # download detail pages -> warren/raw_html/ (git-ignored)
python3 parse_all.py       # -> properties / buildings / land CSV + JSON

# 3. VCGI parcel GIS + join
python3 fetch_vcgi.py      # -> warren_parcels.geojson + warren_parcels_gis.csv
python3 join_nemrc_vcgi.py # -> warren_joined.csv
```

| Script | Role |
|--------|------|
| `fetch_all.sh` | Download all NEMRC camadetail pages (idempotent, 6 workers) |
| `parse_detail.py` | Parse one camadetail HTML page → flat dict (importable) |
| `parse_all.py` | Parse the whole cache → properties / buildings / land / JSON |
| `fetch_vcgi.py` | Pull Warren parcels (geometry + attributes) from VCGI |
| `join_nemrc_vcgi.py` | Join NEMRC ↔ VCGI on PARCID/SPAN, add lon/lat centroid |

## Sources

- **NEMRC property card:** `https://nemrc.info/web_data/vtwarr/camadetailT.php?prop=<PARCEL_ID>` (column `nemrc_url`).
- **VCGI statewide standardized parcels** (public ArcGIS, no auth):
  `https://services1.arcgis.com/BkFxaEFNwHqX3tAw/arcgis/rest/services/FS_VCGI_OPENDATA_Cadastral_VTPARCELS_poly_standardized_parcels_SP_v1/FeatureServer/0`
- **AxisGIS viewer:** <https://www.axisgis.com/WarrenVT> (interactive only; same NEMRC CAMA database).

## Not included

**CAI Property Card PDFs.** The "CAI Property Card" link is generated inside the
AxisGIS app, which is behind reCAPTCHA / AWS-WAF; no public URL pattern resolves
(every guessed path 404s). The PDF is just a formatted view of the NEMRC data
already captured here.
