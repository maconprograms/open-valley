"use client";

import { useMemo } from "react";

interface CategoryData {
  name: string;
  count: number;
  value: number;
  avgValue: number;
  color: string;
  description: string;
}

interface PropertyBreakdownData {
  categories: CategoryData[];
  totalParcels: number;
  totalValue: number;
  headline?: string;
  subheadline?: string;
}

interface PropertyBreakdownProps {
  data: unknown;
}

export default function PropertyBreakdown({ data }: PropertyBreakdownProps) {
  const breakdownData = data as PropertyBreakdownData;

  const sortedCategories = useMemo(() => {
    return [...(breakdownData.categories || [])].sort((a, b) => b.count - a.count);
  }, [breakdownData.categories]);

  if (!breakdownData?.categories?.length) {
    return (
      <div className="p-4 text-gray-400 text-center">
        No property breakdown data available
      </div>
    );
  }

  const formatValue = (v: number) => {
    if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(0)}M`;
    if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}k`;
    return `$${v.toLocaleString()}`;
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-slate-700 to-slate-800 text-white p-6">
        <h2 className="text-2xl font-bold">
          {breakdownData.headline || "Warren Property Composition"}
        </h2>
        <p className="text-slate-300 mt-1">
          {breakdownData.subheadline ||
            `${breakdownData.totalParcels.toLocaleString()} parcels | ${formatValue(breakdownData.totalValue)} total assessed value`}
        </p>
      </div>

      {/* Stacked Bar Visualization */}
      <div className="p-6">
        <div className="mb-6">
          <div className="h-12 rounded-lg overflow-hidden flex shadow-inner">
            {sortedCategories.map((cat) => {
              const pct = (cat.count / breakdownData.totalParcels) * 100;
              return (
                <div
                  key={cat.name}
                  className="h-full flex items-center justify-center text-white text-sm font-medium transition-all hover:opacity-90"
                  style={{
                    width: `${pct}%`,
                    backgroundColor: cat.color,
                    minWidth: pct > 3 ? "auto" : "0",
                  }}
                  title={`${cat.name}: ${cat.count} (${pct.toFixed(1)}%)`}
                >
                  {pct > 8 && `${pct.toFixed(0)}%`}
                </div>
              );
            })}
          </div>
        </div>

        {/* Category Cards */}
        <div className="space-y-3">
          {sortedCategories.map((cat) => {
            const pct = (cat.count / breakdownData.totalParcels) * 100;
            const valuePct = (cat.value / breakdownData.totalValue) * 100;

            return (
              <div
                key={cat.name}
                className="border rounded-lg p-4 hover:shadow-md transition-shadow"
                style={{ borderLeftWidth: "4px", borderLeftColor: cat.color }}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-gray-900">{cat.name}</h3>
                      <span
                        className="px-2 py-0.5 rounded-full text-xs font-medium text-white"
                        style={{ backgroundColor: cat.color }}
                      >
                        {pct.toFixed(0)}%
                      </span>
                    </div>
                    <p className="text-sm text-gray-500 mt-1">{cat.description}</p>
                  </div>
                  <div className="text-right ml-4">
                    <p className="text-lg font-bold text-gray-900">
                      {cat.count.toLocaleString()}
                    </p>
                    <p className="text-xs text-gray-500">parcels</p>
                  </div>
                </div>

                {/* Value bar */}
                <div className="mt-3 grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <p className="text-gray-500">Total Value</p>
                    <p className="font-medium">{formatValue(cat.value)}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Avg Value</p>
                    <p className="font-medium">{formatValue(cat.avgValue)}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">% of Tax Base</p>
                    <p className="font-medium">{valuePct.toFixed(1)}%</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Policy Context Footer */}
        <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-100">
          <p className="text-sm text-blue-800">
            <strong>Vermont Policy Context:</strong> Act 73 of 2025 creates separate tax classifications
            for these property types. The Legislature will set tax rate multipliers by July 2028.
          </p>
        </div>
      </div>
    </div>
  );
}
