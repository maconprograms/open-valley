export interface SelectedParcel {
  accountId: string;
  address: string | null;
  taxStatusBucket: TaxStatusBucket | null;
  housingUnitClaims: number | null;
  unitEvidenceLevels: string[];
}

export type TaxStatusBucket = "homestead_filed" | "non_homestead" | "unknown";

export function parcelSummaryLines(parcel: SelectedParcel): string[] {
  return [
    parcel.address || "No address in extract",
    `Tax status: ${formatTaxStatusBucket(parcel.taxStatusBucket)}`,
    `Housing-unit claims: ${parcel.housingUnitClaims ?? "unknown"} (${parcel.unitEvidenceLevels.join(", ") || "unknown evidence"})`,
  ];
}

/**
 * Convert MapLibre feature properties into the small, display-safe shape used
 * by the selected-parcel panel. MapLibre does not preserve every GeoJSON
 * property type: arrays may arrive as JSON strings.
 */
export function normalizeSelectedParcel(value: unknown): SelectedParcel | null {
  if (!isRecord(value)) return null;

  const accountId = readString(value.account_id);
  if (!accountId) return null;

  return {
    accountId,
    address: readString(value.address),
    taxStatusBucket: readTaxStatusBucket(value.tax_status_bucket),
    housingUnitClaims: readNonNegativeInteger(value.housing_unit_claims),
    unitEvidenceLevels: readStringList(value.unit_evidence_levels),
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function readString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function readNonNegativeInteger(value: unknown): number | null {
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isSafeInteger(parsed) && parsed >= 0 ? parsed : null;
}

function readStringList(value: unknown): string[] {
  if (Array.isArray(value)) return value.filter((item): item is string => typeof item === "string");
  if (typeof value !== "string" || !value.trim()) return [];

  try {
    return readStringList(JSON.parse(value));
  } catch {
    return [value];
  }
}

function readTaxStatusBucket(value: unknown): TaxStatusBucket | null {
  return value === "homestead_filed" || value === "non_homestead" || value === "unknown"
    ? value
    : null;
}

function formatTaxStatusBucket(value: TaxStatusBucket | null): string {
  if (value === "homestead_filed") return "Homestead filed";
  if (value === "non_homestead") return "Non-homestead";
  return "Unknown";
}
