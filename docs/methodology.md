# Methodology

## Scope

Open Valley is a work in progress for Vermont's Mad River Valley. Warren is the
only released town. Future towns require a separate validated source run and
their own public release; they do not change the meaning of the Warren release.

## What is published

Each release contains an allowlisted map projection, summary, homestead trend,
coverage measures, and provider-level provenance. The release identifies its
town, source run, retrieval time and timezone, schema/release version, and
aggregate checksums.

The map is a public parcel projection. It may include a property address,
geometry, GIS-match category, `HSDECL` tax-status bucket, and unit-evidence
summary. It does not include owner names, mailing addresses, review records,
raw source rows, or identifiers used to retrieve private records.

## Reading `HSDECL`

`HSDECL` is shown as a homestead-filing observation from an available tax
record. It does not establish occupancy, residency, rental activity, commercial
use, or second-home use. A non-homestead observation does not establish any of
those things either.

Counts use their displayed denominators. Matched geometry and known-homestead
coverage are shown so an omitted or unknown record is not treated as evidence.
The publication bar requires complete artifact/provenance validation, a clean
restricted-data scan, at least 96% geometry and known-homestead coverage, and a
retrieval no more than 90 days old unless the site says the release is stale or
unavailable.

## Provenance and corrections

Provider links are collection-level origins, not links to individual property
records. The project retains raw imports and any human review outside the public
release boundary. A correction to a private source or review record does not
retroactively rewrite a published release; it is assessed in a later validated
source run.
