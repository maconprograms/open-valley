# Warren human-review ledger

This directory is an append-only, local-review layer for correcting how the
project interprets data quality. It never edits or replaces NEMRC, VCGI, or
PTTR source records.

Create `property_reviews.jsonl` when a review is ready to record. Each line is
one JSON object, for example:

```json
{
  "id": "review:warren:0090058:mailing-address:2026-08-04",
  "account_id": "warren:0090058",
  "source_run_id": "warren-2da137d198aa05ec",
  "subject": "mailing_address",
  "status": "contradicted",
  "reviewed_at": "2026-08-04T12:00:00Z",
  "reviewed_by": "local reviewer",
  "evidence_summary": "Owner confirmed the published mailing address is stale.",
  "source_observation_ids": ["ownership:warren:0090058:1"]
}
```

Allowed `subject` values are `mailing_address`, `homestead_filing`, and
`occupancy`; allowed `status` values are `confirmed`, `contradicted`, and
`needs_follow_up`. No review record means `unreviewed`. A review applies only
to the exact `source_run_id` it names. Re-record it against a refreshed source
run if its supporting observation is still relevant.

Use `homestead_filing` to review whether the published `HSDECL` observation is
correctly represented, and `occupancy` only when there is documented evidence
about actual use. Neither changes the raw `HSDECL` value or map bucket. A
confirmed occupancy finding is a local, attributable observation—not a new tax
determination.

This is a local ledger, not a public API. Keep the reviewer identity and any
supporting evidence in the project-controlled review workflow.
