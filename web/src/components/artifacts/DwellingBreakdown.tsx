"use client";

interface DwellingBreakdownData {
  total_dwellings: number;
  homestead_count: number;
  nhs_residential_count: number;
  nhs_nonresidential_count: number;
  str_count: number;
  headline: string;
  use_type_breakdown: Record<string, number>;
}

interface DwellingBreakdownProps {
  data: unknown;
}

// Use type labels for display
const USE_TYPE_LABELS: Record<string, string> = {
  owner_occupied_primary: "Owner Primary Residence",
  owner_occupied_secondary: "Owner Second Home",
  short_term_rental: "Short-Term Rental",
  long_term_rental: "Long-Term Rental",
  vacant: "Vacant",
  unknown: "Unknown",
};

export default function DwellingBreakdown({ data }: DwellingBreakdownProps) {
  const breakdown = data as DwellingBreakdownData;

  // Calculate percentages
  const homesteadPct = breakdown.total_dwellings > 0
    ? ((breakdown.homestead_count / breakdown.total_dwellings) * 100).toFixed(1)
    : "0";
  const nhsResPct = breakdown.total_dwellings > 0
    ? ((breakdown.nhs_residential_count / breakdown.total_dwellings) * 100).toFixed(1)
    : "0";
  const strPct = breakdown.total_dwellings > 0
    ? ((breakdown.str_count / breakdown.total_dwellings) * 100).toFixed(1)
    : "0";

  // Sort use types by count
  const sortedUseTypes = Object.entries(breakdown.use_type_breakdown || {}).sort(
    ([, a], [, b]) => b - a
  );

  return (
    <div className="space-y-6">
      {/* Headline */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-4 border border-blue-200">
        <h3 className="text-lg font-semibold text-blue-900">{breakdown.headline}</h3>
        <p className="text-sm text-blue-700 mt-1">
          Based on Vermont Act 73 (2025) dwelling classifications
        </p>
      </div>

      {/* Tax Classification Cards */}
      <div className="grid grid-cols-3 gap-4">
        {/* HOMESTEAD */}
        <div className="bg-white rounded-lg border-2 border-green-500 p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
            <span className="text-sm font-medium text-gray-600">HOMESTEAD</span>
          </div>
          <div className="text-2xl font-bold text-green-700">
            {breakdown.homestead_count.toLocaleString()}
          </div>
          <div className="text-sm text-gray-500">{homesteadPct}% of dwellings</div>
          <div className="text-xs text-gray-400 mt-1">Primary Residences</div>
        </div>

        {/* NHS_RESIDENTIAL */}
        <div className="bg-white rounded-lg border-2 border-orange-500 p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-3 h-3 rounded-full bg-orange-500"></div>
            <span className="text-sm font-medium text-gray-600">NHS_RESIDENTIAL</span>
          </div>
          <div className="text-2xl font-bold text-orange-700">
            {breakdown.nhs_residential_count.toLocaleString()}
          </div>
          <div className="text-sm text-gray-500">{nhsResPct}% of dwellings</div>
          <div className="text-xs text-gray-400 mt-1">Second Homes + STRs</div>
        </div>

        {/* NHS_NONRESIDENTIAL */}
        <div className="bg-white rounded-lg border-2 border-red-500 p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-3 h-3 rounded-full bg-red-500"></div>
            <span className="text-sm font-medium text-gray-600">NHS_NONRES</span>
          </div>
          <div className="text-2xl font-bold text-red-700">
            {breakdown.nhs_nonresidential_count.toLocaleString()}
          </div>
          <div className="text-sm text-gray-500">
            {breakdown.total_dwellings > 0
              ? ((breakdown.nhs_nonresidential_count / breakdown.total_dwellings) * 100).toFixed(1)
              : "0"}% of dwellings
          </div>
          <div className="text-xs text-gray-400 mt-1">Commercial / LTR</div>
        </div>
      </div>

      {/* STR Highlight */}
      <div className="bg-amber-50 rounded-lg p-4 border border-amber-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🏠</span>
            <div>
              <div className="font-medium text-amber-900">Short-Term Rentals</div>
              <div className="text-sm text-amber-700">Dwellings used as STRs</div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-amber-700">
              {breakdown.str_count.toLocaleString()}
            </div>
            <div className="text-sm text-amber-600">{strPct}% of all dwellings</div>
          </div>
        </div>
      </div>

      {/* Use Type Breakdown */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h4 className="text-sm font-semibold text-gray-700 mb-3">By Use Type</h4>
        <div className="space-y-2">
          {sortedUseTypes.map(([useType, count]) => {
            const pct = breakdown.total_dwellings > 0
              ? (count / breakdown.total_dwellings) * 100
              : 0;
            const label = USE_TYPE_LABELS[useType] || useType;

            return (
              <div key={useType} className="flex items-center gap-3">
                <div className="flex-1">
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-700">{label}</span>
                    <span className="text-gray-500">
                      {count.toLocaleString()} ({pct.toFixed(1)}%)
                    </span>
                  </div>
                  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 rounded-full"
                      style={{ width: `${pct}%` }}
                    ></div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Total */}
      <div className="text-center text-gray-500 text-sm">
        Total: <span className="font-semibold text-gray-700">{breakdown.total_dwellings.toLocaleString()}</span> dwellings
      </div>
    </div>
  );
}
