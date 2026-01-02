"use client";

import StatCard from "./StatCard";

interface DashboardStats {
  parcels: {
    count: number;
    total_value: number;
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

function formatCurrency(value: number): string {
  if (value >= 1_000_000_000) {
    return `$${(value / 1_000_000_000).toFixed(1)}B`;
  }
  if (value >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(0)}M`;
  }
  if (value >= 1_000) {
    return `$${(value / 1_000).toFixed(0)}K`;
  }
  return `$${value.toLocaleString()}`;
}

export default function StatsGrid({ stats }: StatsGridProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <StatCard
        value={stats.parcels.count.toLocaleString()}
        label="Total Parcels"
        subtext={formatCurrency(stats.parcels.total_value) + " assessed value"}
        color="blue"
      />
      <StatCard
        value={stats.dwellings.total.toLocaleString()}
        label="Total Dwellings"
        subtext="Habitable residential units"
        color="slate"
      />
      <StatCard
        value={`${stats.dwellings.homestead.percent}%`}
        label="Primary Residences"
        subtext={`${stats.dwellings.homestead.count.toLocaleString()} homestead filings`}
        color="green"
      />
      <StatCard
        value={`${stats.dwellings.nhs_residential.percent}%`}
        label="Second Homes"
        subtext={`${stats.dwellings.nhs_residential.count.toLocaleString()} non-homestead dwellings`}
        color="orange"
      />
    </div>
  );
}
