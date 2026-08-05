# Public-release safety rules

- Keep raw source data, personal data, human reviews, credentials, and logs
  containing them out of Git, public artifacts, browser responses, and images.
- Public services read versioned release artifacts only. They do not connect to
  the protected ledger.
- Browser requests stay same-origin through the web service; do not restore a
  direct public API base or permissive browser access.
- Public schemas are strict allowlists. Unknown fields, including nested fields,
  fail closed.
- Only operators handle private imports, exports, backups, and review records.
- Keep claims evidence-bound. `HSDECL` is a filing observation, not evidence of
  occupancy, residency, rental activity, commercial use, or second-home use.
- Run public-release preflight checks before any history rewrite or deployment.
- If a launch fails, do not restore a legacy or raw-data image. Use only a
  validated redacted release or leave the hostname unrouted.
