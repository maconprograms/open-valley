import unittest
from datetime import UTC, date, datetime

from pydantic import ValidationError

from src.warren_baseline.schema import (
    NormalizedPartyMatch,
    OwnershipObservation,
    PartyMatchConfidence,
    PartyMatchReviewState,
    PropertyAccount,
    SourceReference,
    SourceRun,
)


def source_reference() -> SourceReference:
    return SourceReference(
        source_run_id="warren-2026-08-03",
        source_key="nemrc:0010001",
        source_url="https://example.test/property/0010001",
        source_fields=["owner", "parcel_id"],
        retrieved_at=datetime(2026, 8, 3, tzinfo=UTC),
    )


class EvidenceSchemaTests(unittest.TestCase):
    def test_source_run_preserves_retrieval_and_effective_dates(self):
        run = SourceRun(
            id="warren-2026-08-03",
            town="Warren",
            retrieved_at=datetime(2026, 8, 3, tzinfo=UTC),
            source_effective_date=date(2025, 4, 1),
            status="validated",
        )

        payload = run.model_dump(mode="json")

        self.assertEqual(payload["source_effective_date"], "2025-04-01")
        self.assertEqual(payload["retrieved_at"], "2026-08-03T00:00:00Z")

    def test_accounts_with_shared_span_remain_distinct(self):
        first = PropertyAccount(
            id="warren:0010001",
            town="Warren",
            nemrc_parcel_id="0010001",
            parcid="001000-1",
            span="690-219-10513",
            source=source_reference(),
        )
        second = PropertyAccount(
            id="warren:0010002",
            town="Warren",
            nemrc_parcel_id="0010002",
            parcid="001000-2",
            span="690-219-10513",
            source=source_reference(),
        )

        self.assertNotEqual(first.id, second.id)
        self.assertEqual(first.span, second.span)

    def test_source_reference_requires_locator_and_field_provenance(self):
        with self.assertRaises(ValidationError):
            SourceReference(
                source_run_id="warren-2026-08-03",
                source_key="nemrc:0010001",
                source_url="https://example.test/property/0010001",
                source_fields=[],
                retrieved_at=datetime(2026, 8, 3, tzinfo=UTC),
            )

    def test_normalized_party_match_keeps_source_exact_owner_text(self):
        observation = OwnershipObservation(
            id="ownership:warren:0010001:owner1",
            account_id="warren:0010001",
            owner_text="SYNTHETIC OWNER LIFE ESTATE",
            source=source_reference(),
        )
        match = NormalizedPartyMatch(
            id="match:ownership:warren:0010001:owner1",
            ownership_observation_id=observation.id,
            normalized_party_key="synthetic-owner-life-estate",
            confidence=PartyMatchConfidence.EXACT,
            review_state=PartyMatchReviewState.UNREVIEWED,
            source_owner_text=observation.owner_text,
        )

        self.assertEqual(match.source_owner_text, observation.owner_text)
        self.assertEqual(match.confidence, PartyMatchConfidence.EXACT)


if __name__ == "__main__":
    unittest.main()
