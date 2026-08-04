export interface SelectedParcel {
  accountId: string;
  address: string | null;
  homesteadFiled: boolean | null;
  mailingState: string | null;
  outOfStateMailing: boolean | null;
  housingUnitClaims: number | null;
  unitEvidenceLevels: string[];
}

export function parcelSummaryLines(parcel: SelectedParcel): string[] {
  return [
    parcel.address || "No address in extract",
    `Homestead filed: ${formatObservation(parcel.homesteadFiled)}`,
    `Mailing state: ${parcel.mailingState || "unknown"}`,
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
    homesteadFiled: readBoolean(value.homestead_filed),
    mailingState: readString(value.mailing_state),
    outOfStateMailing: readBoolean(value.out_of_state_mailing),
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

function readBoolean(value: unknown): boolean | null {
  if (typeof value === "boolean") return value;
  if (typeof value !== "string") return null;
  if (value === "true") return true;
  if (value === "false") return false;
  return null;
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

function formatObservation(value: boolean | null): string {
  if (value === null) return "unknown";
  return value ? "yes" : "no";
}
