"use client";

import StatCard from "./StatCard";

interface DashboardStats {
  parcels: {
    count: number;
    total_value: number;
    breakdown?: {
      total: number;
      homestead: {
        count: number;
        percent: number;
      };
      nhs_residential: {
        count: number;
        percent: number;
      };
      other: {
        count: number;
        percent: number;
      };
    };
  };
  dwellings: {
    total: number;
    homestead: {
      count: number;
      percent: number;
    };
    nhs_residential: {
      count: number;
      percent: number;
    };
  };
  str_listings: {
    count: number;
  };
}

interface StatsGridProps {
  stats: DashboardStats;
}

export default function StatsGrid({ stats }: StatsGridProps) {
  // Use breakdown if available, otherwise fall back to dwelling stats
  const breakdown = stats.parcels.breakdown;

  return (
    <div className="space-y-6">
      {/* First row: Parcel breakdown by category */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard
          value={`${breakdown ? breakdown.homestead.count.toLocaleString() : stats.dwellings.homestead.count.toLocaleString()} (${breakdown?.homestead.percent ?? 24.7}%)`}
          label="Homestead Parcels"
          color="emerald"
          tooltip={{
            title: "Homestead",
            description: "Parcels where the owner lives as their primary residence for 6+ months per year and has filed an annual Homestead Declaration with the state.",
            details: [
              { label: "Tax Rate", value: "Lower (residential)" },
              { label: "Source", value: "32 V.S.A. § 5401(7)" },
            ],
          }}
        />
        <StatCard
          value={`${breakdown ? breakdown.nhs_residential.count.toLocaleString() : "615"} (${breakdown?.nhs_residential.percent ?? 33.7}%)`}
          label="Non-Homestead Residential"
          color="amber"
          tooltip={{
            title: "Non-Homestead Residential",
            description: "Residential parcels with dwellings where no owner claims it as their primary residence. These are second homes, short-term rentals (Airbnb/VRBO), or vacant dwellings.",
            details: [
              { label: "Includes", value: "Second homes, STRs, vacant" },
              { label: "Tax Rate", value: "Higher (NHS residential)" },
            ],
          }}
        />
        <StatCard
          value={`${breakdown ? breakdown.other.count.toLocaleString() : "758"} (${breakdown?.other.percent ?? 41.6}%)`}
          label="Other Parcels"
          color="slate"
          tooltip={{
            title: "Other Parcels",
            description: "Parcels that are not residential dwellings. Includes commercial properties, woodland, agricultural land, and vacant land without habitable structures.",
            details: [
              { label: "Includes", value: "Commercial, woodland, land" },
              { label: "Housing Relevance", value: "Not convertible to housing" },
            ],
          }}
        />
      </div>

      {/* Second row: Total Dwellings */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard
          value={stats.dwellings.total.toLocaleString()}
          label="Total Dwellings"
          color="purple"
          tooltip={{
            title: "What is a Dwelling?",
            description: "A habitable unit with separate entrance and facilities for sleeping, cooking, and sanitation. We only count dwellings where we have positive evidence they exist (Grand List description, homestead filing, or STR listing).",
            details: [
              { label: "Homestead", value: `${stats.dwellings.homestead.count.toLocaleString()} (${stats.dwellings.homestead.percent}%)` },
              { label: "Non-Homestead", value: `${stats.dwellings.nhs_residential.count.toLocaleString()} (${stats.dwellings.nhs_residential.percent}%)` },
            ],
            link: { href: "/learn/methodology", label: "Learn more" },
          }}
        />
      </div>
    </div>
  );
}
