import { describe, expect, it } from "vitest";

import { normalizeSelectedParcel, parcelSummaryLines } from "./mapProperties";

describe("normalizeSelectedParcel", () => {
  it("parses MapLibre's serialized GeoJSON array properties", () => {
    expect(normalizeSelectedParcel({
      account_id: "warren:0010001",
      address: "15 BROOK RD",
      homestead_filed: "true",
      mailing_state: "VT",
      out_of_state_mailing: "false",
      housing_unit_claims: "1",
      unit_evidence_levels: '["documented", "inferred"]',
    })).toEqual({
      accountId: "warren:0010001",
      address: "15 BROOK RD",
      homesteadFiled: true,
      mailingState: "VT",
      outOfStateMailing: false,
      housingUnitClaims: 1,
      unitEvidenceLevels: ["documented", "inferred"],
    });
  });

  it("keeps malformed optional values from crashing the details panel", () => {
    expect(normalizeSelectedParcel({
      account_id: "warren:0010002",
      housing_unit_claims: "not a number",
      unit_evidence_levels: "not JSON",
    })).toMatchObject({
      accountId: "warren:0010002",
      housingUnitClaims: null,
      unitEvidenceLevels: ["not JSON"],
    });
    expect(normalizeSelectedParcel({ unit_evidence_levels: "[]" })).toBeNull();
  });

  it("formats a concise, evidence-labeled map rollover", () => {
    const parcel = normalizeSelectedParcel({
      account_id: "warren:0010001",
      address: "15 BROOK RD",
      homestead_filed: true,
      mailing_state: "VT",
      housing_unit_claims: 1,
      unit_evidence_levels: '["documented"]',
    });

    expect(parcel && parcelSummaryLines(parcel)).toEqual([
      "15 BROOK RD",
      "Homestead filed: yes",
      "Mailing state: VT",
      "Housing-unit claims: 1 (documented)",
    ]);
  });
});
