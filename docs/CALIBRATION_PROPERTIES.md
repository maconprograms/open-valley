# Calibration Properties: Woods Road

These four properties serve as ground truth for testing and calibrating our dwelling inference model.

---

## Summary Table

| # | Address | Owner | Lives | Dwellings | Use | Classification |
|---|---------|-------|-------|-----------|-----|----------------|
| 1 | 488 Woods Rd S | Phillips | Warren, VT | 1 | Owner-occupied primary | HOMESTEAD |
| 2 | 448 Woods Rd S | Tremblay/Culmone | Harvard, MA | 1 | Second home | NHS_RESIDENTIAL |
| 3 | 200 Woods Rd S | Schulthess Fabio | Switzerland | 2* | Main + LTR (ADU) | NHS_NONRESIDENTIAL |
| 4 | 94 Woods Rd N | Mad River LLC | Brooklyn, NY | 1 | Short-term rental | NHS_RESIDENTIAL |

*ADU not in Grand List - requires manual addition

---

## Property 1: Phillips Family — 488 Woods Rd South

**Ground Truth**: Year-round residents with one single-family home

### Vermont Grand List Data
| Field | Value | Notes |
|-------|-------|-------|
| SPAN | 690-219-11993 | |
| Owner | PHILLIPS III ROBERT M & EMILY | |
| Mailing State | CA | *Stale - family moved from Irvine to Warren* |
| CAT | R2 | **WRONG** - implies multi-family |
| DESCPROP | "7.37 ACRES & DWL" | **CORRECT** - "DWL" = singular |
| HSDECL | Y | Homestead declared |
| HSTED_FLV | $505,800 (100%) | Full value is homestead |

### What's Wrong in Our Data
- **Created 2 dwellings** because CAT=R2 triggered multi-family logic
- **Matched "The Vines" STR** to this parcel (wrong - different property)

### Correct State
```
Parcel: 690-219-11993
└── Dwelling 1: Main house (3br/2.5ba)
    ├── tax_classification: HOMESTEAD
    ├── use_type: owner_occupied_primary
    └── str_listing_id: NULL
```

---

## Property 2: Tremblay/Culmone — 448 Woods Rd South

**Ground Truth**: Massachusetts second-home owners

### Vermont Grand List Data
| Field | Value | Notes |
|-------|-------|-------|
| SPAN | 690-219-13192 | |
| Owner | CULMONE FRANK D / TREMBLAY ERICA | |
| Mailing State | MA | Harvard, MA - confirms out-of-state |
| CAT | R2 | **WRONG** - implies multi-family |
| DESCPROP | "8.15 ACRES & DWL." | **CORRECT** - singular dwelling |
| HSDECL | N | No homestead (correct) |
| HSTED_FLV | $0 (0%) | No homestead value |

### What's Wrong in Our Data
- **Created 2 dwellings** because CAT=R2

### Correct State
```
Parcel: 690-219-13192
└── Dwelling 1: Single-family home
    ├── tax_classification: NHS_RESIDENTIAL
    ├── use_type: owner_occupied_secondary
    └── str_listing_id: NULL
```

---

## Property 3: Fabio Schulthess — 200 Woods Rd South

**Ground Truth**: Swiss owner with long-term renter in ADU above garage

### Vermont Grand List Data
| Field | Value | Notes |
|-------|-------|-------|
| SPAN | 690-219-12656 | |
| Owner | SCHULTHESS FABIO | |
| Mailing State | (blank) | Actually: Ascona, Switzerland |
| CAT | R1 | Single-family (technically correct for main house) |
| DESCPROP | "3.1 ACRES: & DWL" | Only knows about main dwelling |
| HSDECL | N | No homestead |
| HSTED_FLV | $0 (0%) | |

### What's Wrong in Our Data
- **Missing ADU** - apartment above garage has long-term renter
- **Classification wrong** - should be NHS_NONRESIDENTIAL (LTR)

### Correct State
```
Parcel: 690-219-12656
├── Dwelling 1: Main house
│   ├── tax_classification: NHS_RESIDENTIAL (if owner uses) or NHS_NONRESIDENTIAL (if never uses)
│   └── use_type: owner_occupied_secondary (needs verification)
│
└── Dwelling 2: ADU above garage **[MANUAL ADD]**
    ├── tax_classification: NHS_NONRESIDENTIAL
    ├── use_type: long_term_rental
    └── notes: "Tenant lives above garage per local knowledge"
```

---

## Property 4: Mad River LLC — 94 Woods Rd North

**Ground Truth**: Brooklyn LLC operating a short-term rental

### Vermont Grand List Data
| Field | Value | Notes |
|-------|-------|-------|
| SPAN | 690-219-12576 | |
| Owner | MAD RIVER LLC | |
| Mailing State | NY | 255 Clinton Street, Brooklyn NY 11201 |
| CAT | R1 | Correct |
| DESCPROP | "2.6 ACRES & DWL:" | Correct |
| HSDECL | N | No homestead (correct for LLC) |

### STR Match
| Field | Value |
|-------|-------|
| Airbnb Listing | [53252922](https://www.airbnb.com/rooms/53252922) |
| STR Name | HYGGE HAUS - Mountain Views Minutes from Sugarbush |
| Bedrooms | 4 |
| Match Confidence | High (listing_id matches Airbnb URL) |

### Current Data Status
- **Correct!** Single dwelling properly matched to STR listing

### Correct State
```
Parcel: 690-219-12576
└── Dwelling 1: Single-family home
    ├── tax_classification: NHS_RESIDENTIAL
    ├── use_type: short_term_rental
    └── str_listing_id: (linked to HYGGE HAUS)
```

---

## Key Learnings

### 1. CAT Code is Unreliable
The Grand List `CAT` field (R1, R2, etc.) often contradicts `DESCPROP`:

| SPAN | CAT | DESCPROP | Reality |
|------|-----|----------|---------|
| 690-219-11993 | R2 (multi) | "& DWL" (singular) | 1 dwelling |
| 690-219-13192 | R2 (multi) | "& DWL" (singular) | 1 dwelling |

**Fix**: Parse DESCPROP for dwelling count, ignore CAT for unit counting.

### 2. DESCPROP Patterns
| Pattern | Meaning | Dwellings |
|---------|---------|-----------|
| `& DWL` | Single dwelling | 1 |
| `& DWL.` | Single dwelling | 1 |
| `& DWL:` | Single dwelling | 1 |
| `& 2 DWLS` | Two dwellings | 2 |
| `& MF` | Multi-family | Parse further |
| `& CONDO` | Condo unit | 1 |

### 3. ADUs Are Invisible
The Grand List doesn't capture accessory dwelling units (ADUs) like:
- Apartments above garages
- In-law suites
- Converted barns

**These require manual addition based on local knowledge.**

### 4. Mailing Address Can Be Stale
Phillips family shows CA mailing address but actually lives in Warren. The `HSDECL=Y` and `HSTED_FLV=100%` are more reliable indicators of residency than mailing address.

### 5. LLC Ownership = Almost Never Primary
If owner is an LLC (like "MAD RIVER LLC"), it's almost certainly:
- An investment property
- An STR
- A vacation home

LLCs cannot file homestead declarations in Vermont.

---

## Validation Queries

```sql
-- Check our calibration properties
SELECT
    p.address,
    p.property_type as imported_type,
    COUNT(d.id) as dwelling_count,
    STRING_AGG(d.tax_classification, ', ') as classifications
FROM parcels p
LEFT JOIN dwellings d ON d.parcel_id = p.id
WHERE p.span IN ('690-219-11993', '690-219-13192', '690-219-12656', '690-219-12576')
GROUP BY p.span, p.address, p.property_type
ORDER BY p.address;

-- Expected results after fixes:
-- 488 Woods Rd S: 1 dwelling, HOMESTEAD
-- 448 Woods Rd S: 1 dwelling, NHS_RESIDENTIAL
-- 200 Woods Rd S: 2 dwellings, NHS_RESIDENTIAL + NHS_NONRESIDENTIAL
-- 94 Woods Rd N:  1 dwelling, NHS_RESIDENTIAL (STR)
```

---

## Action Items

1. [ ] **Fix import script** - Parse DESCPROP instead of using CAT for dwelling count
2. [ ] **Delete incorrect dwellings** - Remove phantom 2nd dwellings from 488 and 448
3. [ ] **Add Fabio's ADU** - Manually create dwelling for apartment above garage
4. [ ] **Fix The Vines STR match** - Find correct parcel for this listing
5. [ ] **Update Phillips mailing address** - Or note that HSDECL is authoritative
