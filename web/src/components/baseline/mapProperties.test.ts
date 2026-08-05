import { describe, expect, it } from "vitest";

import {
  normalizePublicMap,
  findPublicParcels,
  parcelSummaryLines,
} from "./mapProperties";

describe("normalizePublicMap", () => {
  it("accepts the redacted map shape and assigns an internal selection key", () => {
    expect(normalizePublicMap({
      type: "FeatureCollection",
      features: [{
        type: "Feature",
        geometry: { type: "Point", coordinates: [-72.86, 44.12] },
        properties: {
          address: "15 BROOK RD",
          gis_match: "exact_parcid",
          tax_status_bucket: "homestead_filed",
          housing_unit_claims: 1,
          unit_evidence_levels: ["documented", "inferred"],
        },
      }],
    })).toMatchObject({
      parcels: [{
        key: "parcel-0",
        address: "15 BROOK RD",
        tax_status_bucket: "homestead_filed",
        housing_unit_claims: 1,
        unit_evidence_levels: ["documented", "inferred"],
      }],
      malformedFeatures: 0,
    });
  });

  it("drops malformed public features without making the whole map unusable", () => {
    expect(normalizePublicMap({
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          geometry: { type: "Point", coordinates: [-72.86, 44.12] },
          properties: {
            address: "15 BROOK RD",
            gis_match: "exact_parcid",
            tax_status_bucket: "unknown",
            housing_unit_claims: 0,
            unit_evidence_levels: ["unknown"],
          },
        },
        { type: "Feature", geometry: null, properties: {} },
      ],
    })).toMatchObject({
      parcels: [expect.objectContaining({ address: "15 BROOK RD" })],
      malformedFeatures: 1,
    });
  });

  it("returns a small, deterministic address-search result set without an account identifier", () => {
    const parsed = normalizePublicMap({
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          geometry: { type: "Point", coordinates: [-72.86, 44.12] },
          properties: { address: "ZINC RD", gis_match: "exact_span", tax_status_bucket: "unknown", housing_unit_claims: 0, unit_evidence_levels: ["unknown"] },
        },
        {
          type: "Feature",
          geometry: { type: "Point", coordinates: [-72.87, 44.13] },
          properties: { address: "APPLE RD", gis_match: "exact_parcid", tax_status_bucket: "homestead_filed", housing_unit_claims: 1, unit_evidence_levels: ["documented"] },
        },
      ],
    });

    expect(findPublicParcels(parsed.parcels, "r", 1)).toEqual([]);
    expect(findPublicParcels(parsed.parcels, "rd").map((parcel) => parcel.address)).toEqual([
      "APPLE RD",
      "ZINC RD",
    ]);
    expect(findPublicParcels(parsed.parcels, "rd", 1).map((parcel) => parcel.address)).toEqual([
      "APPLE RD",
    ]);
  });

  it("formats a concise, evidence-labeled public parcel summary", () => {
    const [parcel] = normalizePublicMap({
      type: "FeatureCollection",
      features: [{
        type: "Feature",
        geometry: { type: "Point", coordinates: [-72.86, 44.12] },
        properties: { address: "15 BROOK RD", gis_match: "exact_parcid", tax_status_bucket: "homestead_filed", housing_unit_claims: 1, unit_evidence_levels: ["documented"] },
      }],
    }).parcels;

    expect(parcelSummaryLines(parcel)).toEqual([
      "15 BROOK RD",
      "Tax status: Homestead filed",
      "Housing-unit claims: 1 (documented)",
    ]);
  });
});
