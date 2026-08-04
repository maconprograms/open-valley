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

const apiBase = process.env.NEXT_PUBLIC_BASELINE_API_URL || "http://localhost:8998";

function Percentage({ numerator, denominator }: { numerator: number; denominator: number }) {
  if (!denominator) return <>—</>;
  return <>{((numerator / denominator) * 100).toFixed(1)}%</>;
}

export default function BaselineDashboard() {
  const [summary, setSummary] = useState<BaselineSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${apiBase}/api/baseline/summary`)
      .then(async (response) => {
        if (!response.ok) throw new Error(`API returned ${response.status}`);
        return response.json() as Promise<BaselineSummary>;
      })
      .then(setSummary)
      .catch(() => {
        setError("The current Warren source run is unavailable. No fallback figures are shown.");
      });
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
