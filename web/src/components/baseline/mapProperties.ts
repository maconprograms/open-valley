export type TaxStatusBucket = "homestead_filed" | "non_homestead" | "unknown";

type PublicGeometryType = "Point" | "LineString" | "Polygon" | "MultiPolygon";

export interface PublicMapFeature {
  type: "Feature";
  geometry: {
    type: PublicGeometryType;
    coordinates: unknown;
  };
  properties: {
    address: string | null;
    gis_match: "exact_parcid" | "exact_span" | "coordinate_only" | "unmatched";
    tax_status_bucket: TaxStatusBucket;
    housing_unit_claims: number;
    unit_evidence_levels: Array<"documented" | "inferred" | "unknown" | "excluded">;
  };
}

export type PublicParcel = PublicMapFeature["properties"] & {
  key: string;
  geometry: PublicMapFeature["geometry"];
};

export interface NormalizedPublicMap {
  parcels: PublicParcel[];
  malformedFeatures: number;
}

/**
 * The map endpoint has no account, owner, mailing, or review identifier. This
 * browser-only key exists solely to synchronize a public feature with its
 * keyboard-operable list item; it is never requested from or sent to the API.
 */
export function normalizePublicMap(value: unknown): NormalizedPublicMap {
  if (!isRecord(value) || value.type !== "FeatureCollection" || !Array.isArray(value.features)) {
    return { parcels: [], malformedFeatures: 1 };
  }

  let malformedFeatures = 0;
  const parcels = value.features.flatMap((feature, index) => {
    const normalized = normalizePublicFeature(feature, `parcel-${index}`);
    if (!normalized) {
      malformedFeatures += 1;
      return [];
    }
    return [normalized];
  });

  return { parcels, malformedFeatures };
}

export function parcelSummariesFromMap(parcels: PublicParcel[]): PublicParcel[] {
  return [...parcels].sort((left, right) => {
    const addressOrder = parcelLabel(left).localeCompare(parcelLabel(right), "en", { sensitivity: "base" });
    return addressOrder || left.key.localeCompare(right.key);
  });
}

export function parcelSummaryLines(parcel: PublicParcel): string[] {
  return [
    parcelLabel(parcel),
    `Tax status: ${formatTaxStatusBucket(parcel.tax_status_bucket)}`,
    `Housing-unit claims: ${parcel.housing_unit_claims} (${parcel.unit_evidence_levels.join(", ") || "unknown evidence"})`,
  ];
}

export function parcelLabel(parcel: PublicParcel): string {
  return parcel.address || "Address unavailable in this release";
}

export function mapFeatureCollection(parcels: PublicParcel[]) {
  return {
    type: "FeatureCollection" as const,
    features: parcels.map((parcel) => ({
      type: "Feature" as const,
      geometry: parcel.geometry,
      properties: {
        address: parcel.address,
        gis_match: parcel.gis_match,
        tax_status_bucket: parcel.tax_status_bucket,
        housing_unit_claims: parcel.housing_unit_claims,
        unit_evidence_levels: parcel.unit_evidence_levels,
        __parcel_key: parcel.key,
      },
    })),
  };
}

export function publicMapFeatureKey(value: unknown): string | null {
  return isRecord(value) && typeof value.__parcel_key === "string" ? value.__parcel_key : null;
}

function normalizePublicFeature(value: unknown, key: string): PublicParcel | null {
  if (!isRecord(value) || value.type !== "Feature" || !isRecord(value.geometry) || !isRecord(value.properties)) {
    return null;
  }

  const type = value.geometry.type;
  const coordinates = value.geometry.coordinates;
  if (!isGeometryType(type) || !hasCoordinates(coordinates)) return null;

  const address = value.properties.address;
  const gisMatch = value.properties.gis_match;
  const taxStatus = value.properties.tax_status_bucket;
  const unitClaims = value.properties.housing_unit_claims;
  const evidence = value.properties.unit_evidence_levels;
  if (
    !(typeof address === "string" || address === null) ||
    !isGisMatch(gisMatch) ||
    !isTaxStatusBucket(taxStatus) ||
    typeof unitClaims !== "number" || !Number.isSafeInteger(unitClaims) || unitClaims < 0 ||
    !Array.isArray(evidence) || !evidence.every(isEvidenceLevel)
  ) {
    return null;
  }

  return {
    key,
    address,
    gis_match: gisMatch,
    tax_status_bucket: taxStatus,
    housing_unit_claims: unitClaims,
    unit_evidence_levels: evidence,
    geometry: { type, coordinates },
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isGeometryType(value: unknown): value is PublicGeometryType {
  return value === "Point" || value === "LineString" || value === "Polygon" || value === "MultiPolygon";
}

function hasCoordinates(value: unknown): boolean {
  if (typeof value === "number") return Number.isFinite(value);
  return Array.isArray(value) && value.length > 0 && value.every(hasCoordinates);
}

function isTaxStatusBucket(value: unknown): value is TaxStatusBucket {
  return value === "homestead_filed" || value === "non_homestead" || value === "unknown";
}

function isGisMatch(value: unknown): value is PublicParcel["gis_match"] {
  return value === "exact_parcid" || value === "exact_span" || value === "coordinate_only" || value === "unmatched";
}

function isEvidenceLevel(value: unknown): value is PublicParcel["unit_evidence_levels"][number] {
  return value === "documented" || value === "inferred" || value === "unknown" || value === "excluded";
}

function formatTaxStatusBucket(value: TaxStatusBucket): string {
  if (value === "homestead_filed") return "Homestead filed";
  if (value === "non_homestead") return "Non-homestead";
  return "Unknown";
}
