"use client";

import { useEffect, useState } from "react";

import BaselineMap from "./BaselineMap";

type Coverage = {
  accounts_denominator: number;
  matched_geometries: number;
  geometry_denominator: number;
  known_homestead: number;
  homestead_denominator: number;
};

interface BaselineSummary {
  schema_version: string;
  release_version: string;
  town: string;
  source_run_id: string;
  coverage: Coverage;
  counts: { tax_accounts: number; housing_unit_claims: number };
  tax_status_buckets: { homestead_filed: number; non_homestead: number; unknown: number };
}

interface HomesteadTrend {
  measure: string;
  observations: Array<{
    grand_list_year: number;
    tax_accounts: number;
    homestead_filed: number;
    unknown_homestead: number;
  }>;
}

interface ProviderDescriptor {
  provider: string;
  provider_url: string;
  retrieved_at: string;
  retrieved_timezone: string;
  aggregate_checksum: string;
  field_labels: string[];
}

interface Providers {
  schema_version: string;
  release_version: string;
  town: string;
  source_run_id: string;
  providers: ProviderDescriptor[];
}

function Percentage({ numerator, denominator }: { numerator: number; denominator: number }) {
  if (!denominator) return <>—</>;
  return <>{((numerator / denominator) * 100).toFixed(1)}%</>;
}

function publicError(message: string) {
  return message === "AbortError" ? null : "The current public Warren release is unavailable. No fallback figures are shown.";
}

export default function BaselineDashboard() {
  const [summary, setSummary] = useState<BaselineSummary | null>(null);
  const [trend, setTrend] = useState<HomesteadTrend | null>(null);
  const [providers, setProviders] = useState<Providers | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const request = <T,>(path: string) => fetch(path, { signal: controller.signal }).then(async (response) => {
      if (!response.ok) throw new Error(`Public release API returned ${response.status}`);
      return response.json() as Promise<T>;
    });

    void request<BaselineSummary>("/api/baseline/summary")
      .then(setSummary)
      .catch((requestError: unknown) => {
        if (requestError instanceof Error) setError(publicError(requestError.name));
      });
    void request<HomesteadTrend>("/api/baseline/trends/homestead").then(setTrend).catch(() => setTrend(null));
    void request<Providers>("/api/baseline/providers").then(setProviders).catch(() => setProviders(null));
    return () => controller.abort();
  }, []);

  const knownHomestead = summary
    ? summary.tax_status_buckets.homestead_filed + summary.tax_status_buckets.non_homestead
    : 0;

  return (
    <div className="space-y-6">
      <section className="rounded-2xl bg-slate-950 px-6 py-8 text-slate-100 sm:px-8">
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-emerald-300">Open Valley · work in progress</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">A public property-data baseline for the Mad River Valley</h1>
        <p className="mt-3 max-w-3xl text-slate-300">Warren is the only released area today. This is a redacted, source-led baseline intended to make the available records, their coverage, and their limits visible—not to make claims beyond them.</p>
        <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-200"><strong>How to read `HSDECL`:</strong> it is a homestead-filing observation from a tax record. Neither homestead nor non-homestead establishes occupancy, residency, rental activity, commercial use, or second-home use.</p>
      </section>

      {error ? <div role="alert" className="rounded-xl border border-amber-300 bg-amber-50 p-5 text-amber-950">{error}</div>
        : !summary ? <div role="status" className="rounded-xl border border-slate-200 bg-white p-5 text-slate-600">Loading the current public release…</div>
          : <>
            <section aria-label="Current public release measures" className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <Metric label="Tax accounts" value={summary.counts.tax_accounts.toLocaleString()} detail="Public-release account count" />
              <Metric label="Homestead filed" value={<Percentage numerator={summary.tax_status_buckets.homestead_filed} denominator={knownHomestead} />} detail={`${summary.tax_status_buckets.homestead_filed.toLocaleString()} filed; ${summary.tax_status_buckets.unknown.toLocaleString()} unknown`} />
              <Metric label="Non-homestead" value={<Percentage numerator={summary.tax_status_buckets.non_homestead} denominator={knownHomestead} />} detail="A tax-field observation; it does not identify property use." />
              <Metric label="Housing-unit claims" value={summary.counts.housing_unit_claims.toLocaleString()} detail="Source-supported claims, separate from tax accounts" />
            </section>

            <BaselineMap coverage={summary.coverage} />
            {trend && <HomesteadTrendTable trend={trend} />}
            <Provenance summary={summary} providers={providers} />
          </>}
    </div>
  );
}

function HomesteadTrendTable({ trend }: { trend: HomesteadTrend }) {
  return <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm" aria-labelledby="homestead-trend-heading">
    <div className="border-b border-slate-200 px-5 py-4">
      <p className="text-sm font-medium uppercase tracking-wide text-emerald-700">Available annual observations</p>
      <h2 id="homestead-trend-heading" className="mt-1 text-xl font-semibold text-slate-950">Homestead filing records</h2>
      <p className="mt-2 max-w-4xl text-sm text-slate-600">{trend.measure}. Values are source observations, not a measure of who lives at a property or how it is used.</p>
    </div>
    <div className="overflow-x-auto"><table className="w-full text-left text-sm">
      <thead className="bg-slate-50 text-slate-600"><tr><th className="px-5 py-3 font-medium">Year</th><th className="px-5 py-3 font-medium">Tax accounts</th><th className="px-5 py-3 font-medium">Homestead filed</th><th className="px-5 py-3 font-medium">Unknown `HSDECL`</th></tr></thead>
      <tbody className="divide-y divide-slate-100">{trend.observations.map((observation) => <tr key={observation.grand_list_year} className="text-slate-700"><td className="px-5 py-3 font-medium text-slate-950">{observation.grand_list_year}</td><td className="px-5 py-3">{observation.tax_accounts.toLocaleString()}</td><td className="px-5 py-3">{observation.homestead_filed.toLocaleString()}</td><td className="px-5 py-3">{observation.unknown_homestead.toLocaleString()}</td></tr>)}</tbody>
    </table></div>
  </section>;
}

function Provenance({ summary, providers }: { summary: BaselineSummary; providers: Providers | null }) {
  return <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm" aria-labelledby="provenance-heading">
    <p className="text-sm font-medium uppercase tracking-wide text-emerald-700">Provenance and coverage</p>
    <h2 id="provenance-heading" className="mt-1 text-xl font-semibold text-slate-950">What this public release contains</h2>
    <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-3">
      <Fact label="Released town" value={summary.town} />
      <Fact label="Source run" value={summary.source_run_id} mono />
      <Fact label="Release version" value={summary.release_version} mono />
      <Fact label="Geometry coverage" value={`${summary.coverage.matched_geometries.toLocaleString()} of ${summary.coverage.geometry_denominator.toLocaleString()} matched`} />
      <Fact label="Known homestead field" value={`${summary.coverage.known_homestead.toLocaleString()} of ${summary.coverage.homestead_denominator.toLocaleString()} known`} />
      <Fact label="Public schema" value={summary.schema_version} mono />
    </dl>
    {providers ? <div className="mt-5 border-t border-slate-200 pt-4">
      <h3 className="font-semibold text-slate-950">Provider origins</h3>
      <ul className="mt-2 space-y-2 text-sm text-slate-700">{providers.providers.map((provider) => <li key={provider.provider}><a className="font-medium text-emerald-800 underline underline-offset-2 focus:outline-2 focus:outline-offset-2 focus:outline-emerald-700" href={provider.provider_url} rel="noreferrer">{provider.provider}</a><span className="text-slate-500"> · retrieved {formatDate(provider.retrieved_at, provider.retrieved_timezone)} · fields: {provider.field_labels.join(", ")}</span></li>)}</ul>
    </div> : <p role="status" className="mt-5 border-t border-slate-200 pt-4 text-sm text-slate-600">Provider provenance is unavailable for this release. No source details are inferred.</p>}
  </section>;
}

function formatDate(value: string, timezone: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? `unavailable (${timezone})` : `${date.toLocaleString(undefined, { timeZone: timezone })} ${timezone}`;
}

function Metric({ label, value, detail }: { label: string; value: React.ReactNode; detail: string }) {
  return <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-sm font-medium text-slate-600">{label}</p><p className="mt-2 text-3xl font-semibold text-slate-950">{value}</p><p className="mt-2 text-sm text-slate-500">{detail}</p></div>;
}

function Fact({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return <div><dt className="font-medium text-slate-500">{label}</dt><dd className={`mt-1 break-words font-semibold text-slate-900 ${mono ? "font-mono text-xs" : ""}`}>{value}</dd></div>;
}
