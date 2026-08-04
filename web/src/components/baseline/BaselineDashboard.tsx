"use client";

import { useEffect, useState } from "react";

import BaselineMap from "./BaselineMap";

type Counts = { yes: number; no: number; unknown: number; known: number };

interface BaselineSummary {
  source_run_id: string;
  source_coverage: Record<string, number>;
  tax_accounts: { total: number };
  housing_unit_claims: {
    total: number;
    by_evidence_level: Record<string, number>;
  };
  homestead_filed: Counts;
  out_of_state_mailing: Counts;
}

interface HomesteadTrendObservation {
  grand_list_year: number;
  source_available_for_warren: boolean;
  grand_list_records_with_parcid: number;
  homestead_filed: number | null;
  known_homestead_denominator: number | null;
  homestead_filed_percent_of_known: number | null;
  category_o_other_excluded: ExclusionSummary | null;
}

interface ExclusionSummary {
  records_removed: number;
  records_remaining: number;
  homestead_filed_percent_of_known: number | null;
}

interface HomesteadTrend {
  measure: string;
  caveat: string;
  observations: HomesteadTrendObservation[];
}

const apiBase = process.env.NEXT_PUBLIC_BASELINE_API_URL || "";

function Percentage({ numerator, denominator }: { numerator: number; denominator: number }) {
  if (!denominator) return <>—</>;
  return <>{((numerator / denominator) * 100).toFixed(1)}%</>;
}

export default function BaselineDashboard() {
  const [summary, setSummary] = useState<BaselineSummary | null>(null);
  const [trend, setTrend] = useState<HomesteadTrend | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${apiBase}/api/baseline/summary`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(`API returned ${response.status}`);
        return response.json() as Promise<BaselineSummary>;
      })
      .then(setSummary)
      .catch((requestError) => {
        if (requestError.name !== "AbortError") {
          setError("The current Warren source run is unavailable. No fallback figures are shown.");
        }
      });
    fetch(`${apiBase}/api/baseline/trends/homestead`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(`API returned ${response.status}`);
        return response.json() as Promise<HomesteadTrend>;
      })
      .then(setTrend)
      .catch((requestError) => {
        if (requestError.name !== "AbortError") setTrend(null);
      });
    return () => controller.abort();
  }, []);

  return (
    <div className="space-y-6">
      <section className="rounded-2xl bg-slate-950 px-6 py-8 text-slate-100 sm:px-8">
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-emerald-300">Warren baseline</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
          Property, homestead filing, and mailing-address facts
        </h1>
        <p className="mt-3 max-w-3xl text-slate-300">
          This dashboard distinguishes tax accounts from housing-unit claims. A homestead filing and an
          out-of-state mailing address are source observations—not proof of year-round occupancy or a
          second-home classification.
        </p>
        {summary && (
          <p className="mt-4 text-sm text-slate-400">
            Current source run: <span className="font-mono text-slate-300">{summary.source_run_id}</span>
          </p>
        )}
      </section>

      {error ? (
        <div className="rounded-xl border border-amber-300 bg-amber-50 p-5 text-amber-950">{error}</div>
      ) : !summary ? (
        <div className="rounded-xl border border-slate-200 bg-white p-5 text-slate-600">Loading source run…</div>
      ) : (
        <>
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <Metric label="Tax accounts" value={summary.tax_accounts.total.toLocaleString()} detail="NEMRC account rows" />
            <Metric
              label="Homestead filed"
              value={<Percentage numerator={summary.homestead_filed.yes} denominator={summary.homestead_filed.known} />}
              detail={`${summary.homestead_filed.yes.toLocaleString()} filed; ${summary.homestead_filed.unknown.toLocaleString()} unknown`}
            />
            <Metric
              label="Out-of-state mailing"
              value={<Percentage numerator={summary.out_of_state_mailing.yes} denominator={summary.out_of_state_mailing.known} />}
              detail={`${summary.out_of_state_mailing.yes.toLocaleString()} accounts; mailing address only`}
            />
            <Metric
              label="Housing-unit claims"
              value={summary.housing_unit_claims.total.toLocaleString()}
              detail={`${(summary.housing_unit_claims.by_evidence_level.documented || 0).toLocaleString()} documented; remainder inferred or unknown`}
            />
          </section>

          <BaselineMap apiBase={apiBase} />

          {trend && <HomesteadTrendTable trend={trend} />}

          <section className="grid gap-4 md:grid-cols-3">
            <Fact label="GIS coverage" value={`${summary.source_coverage.matched_geometries.toLocaleString()} matched`} detail={`${summary.source_coverage.unmatched_accounts.toLocaleString()} tax accounts have no matched parcel geometry.`} />
            <Fact label="PTTR transfers" value={summary.source_coverage.transfer_events.toLocaleString()} detail="Documented transfer records; linked only where a unique SPAN match exists." />
            <Fact label="How to read this" value="Keep denominators visible" detail="Accounts, housing-unit claims, homestead filings, and mailing locations answer different questions." />
          </section>
        </>
      )}
    </div>
  );
}

function HomesteadTrendTable({ trend }: { trend: HomesteadTrend }) {
  const available = trend.observations.filter(
    (observation) => observation.source_available_for_warren && observation.homestead_filed_percent_of_known !== null,
  );
  const first = available[0];
  const last = available.at(-1);
  const change = first && last
    ? last.homestead_filed_percent_of_known! - first.homestead_filed_percent_of_known!
    : null;

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 px-5 py-4">
        <p className="text-sm font-medium uppercase tracking-wide text-emerald-700">Annual Grand List trend</p>
        <h2 className="mt-1 text-xl font-semibold text-slate-950">Homestead filed, 2018–2025</h2>
        <p className="mt-2 max-w-4xl text-sm text-slate-600">{trend.caveat}</p>
        <p className="mt-2 max-w-4xl text-sm text-slate-600">
          Sensitivity: the second rate excludes source category <code>O</code> / <code>Other</code>.
          In the current extract, that category almost entirely overlaps accounts sharing a <code>C-</code>
          SPAN—the source&apos;s condominium/common-area grouping. It is a transparent proxy, not an assertion
          that every excluded record is a condominium.
        </p>
        {change !== null && (
          <p className="mt-3 text-sm font-medium text-slate-800">
            Change from {first!.grand_list_year} to {last!.grand_list_year}: {change.toFixed(2)} percentage points.
          </p>
        )}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="px-5 py-3 font-medium">Grand List year</th>
              <th className="px-5 py-3 font-medium">Filed</th>
              <th className="px-5 py-3 font-medium">Known denominator</th>
              <th className="px-5 py-3 font-medium">All-record rate</th>
              <th className="px-5 py-3 font-medium">Rate excluding O / Other</th>
              <th className="px-5 py-3 font-medium">Coverage note</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {trend.observations.map((observation) => (
              <tr key={observation.grand_list_year} className="text-slate-700">
                <td className="px-5 py-3 font-medium text-slate-950">{observation.grand_list_year}</td>
                <td className="px-5 py-3">{observation.homestead_filed?.toLocaleString() || "—"}</td>
                <td className="px-5 py-3">{observation.known_homestead_denominator?.toLocaleString() || "—"}</td>
                <td className="px-5 py-3 font-semibold">
                  {observation.homestead_filed_percent_of_known === null
                    ? "Unavailable"
                    : `${observation.homestead_filed_percent_of_known.toFixed(2)}%`}
                </td>
                <td className="px-5 py-3 font-semibold text-emerald-800">
                  {observation.category_o_other_excluded?.homestead_filed_percent_of_known === null ||
                  !observation.category_o_other_excluded
                    ? "Unavailable"
                    : `${observation.category_o_other_excluded.homestead_filed_percent_of_known.toFixed(2)}%`}
                  {observation.category_o_other_excluded && (
                    <span className="ml-1 text-xs font-normal text-slate-500">
                      ({observation.category_o_other_excluded.records_removed.toLocaleString()} removed)
                    </span>
                  )}
                </td>
                <td className="px-5 py-3 text-slate-500">
                  {observation.source_available_for_warren
                    ? `${observation.grand_list_records_with_parcid.toLocaleString()} records with PARCID`
                    : "VCGI archive has no usable Warren Grand List join"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Metric({ label, value, detail }: { label: string; value: React.ReactNode; detail: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-medium text-slate-600">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-slate-950">{value}</p>
      <p className="mt-2 text-sm text-slate-500">{detail}</p>
    </div>
  );
}

function Fact({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className="mt-1 font-semibold text-slate-900">{value}</p>
      <p className="mt-2 text-sm text-slate-600">{detail}</p>
    </div>
  );
}
