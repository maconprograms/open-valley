"use client";

import { useEffect, useRef, useState } from "react";

type Filter = "all" | "homestead" | "not_homestead" | "out_of_state";

interface MapFeature {
  properties: {
    account_id: string;
    address?: string | null;
    homestead_filed?: boolean | null;
    mailing_state?: string | null;
    out_of_state_mailing: boolean;
    housing_unit_claims: number;
    unit_evidence_levels: string[];
  };
}

export default function BaselineMap({ apiBase }: { apiBase: string }) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<import("maplibre-gl").Map | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [selected, setSelected] = useState<MapFeature["properties"] | null>(null);
  const [status, setStatus] = useState("Loading parcel map…");

  useEffect(() => {
    if (!container.current || mapRef.current) return;
    let destroyed = false;
    void (async () => {
      const maplibregl = await import("maplibre-gl");
      await import("maplibre-gl/dist/maplibre-gl.css");
      if (destroyed || !container.current) return;
      const map = new maplibregl.Map({
        container: container.current,
        style: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        center: [-72.86, 44.12],
        zoom: 11.7,
      });
      mapRef.current = map;
      map.on("load", async () => {
        try {
          const response = await fetch(`${apiBase}/api/baseline/map`);
          if (!response.ok) throw new Error();
          const data = await response.json();
          map.addSource("baseline-parcels", { type: "geojson", data });
          map.addLayer({
            id: "baseline-parcels-fill",
            type: "fill",
            source: "baseline-parcels",
            paint: {
              "fill-color": [
                "case",
                ["==", ["get", "homestead_filed"], true], "#059669",
                ["==", ["get", "out_of_state_mailing"], true], "#d97706",
                "#64748b",
              ],
              "fill-opacity": 0.62,
            },
          });
          map.addLayer({
            id: "baseline-parcels-line",
            type: "line",
            source: "baseline-parcels",
            paint: { "line-color": "#ffffff", "line-width": 0.45 },
          });
          map.on("click", "baseline-parcels-fill", (event) => {
            const properties = event.features?.[0]?.properties as MapFeature["properties"] | undefined;
            setSelected(properties || null);
          });
          map.on("mouseenter", "baseline-parcels-fill", () => { map.getCanvas().style.cursor = "pointer"; });
          map.on("mouseleave", "baseline-parcels-fill", () => { map.getCanvas().style.cursor = ""; });
          setStatus("");
        } catch {
          setStatus("Map data could not be loaded. No substitute map is shown.");
        }
      });
    })();
    return () => {
      destroyed = true;
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, [apiBase]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map?.getLayer("baseline-parcels-fill")) return;
    const filters: Record<Filter, unknown[] | null> = {
      all: null,
      homestead: ["==", ["get", "homestead_filed"], true],
      not_homestead: ["==", ["get", "homestead_filed"], false],
      out_of_state: ["==", ["get", "out_of_state_mailing"], true],
    };
    map.setFilter("baseline-parcels-fill", filters[filter] as never);
    map.setFilter("baseline-parcels-line", filters[filter] as never);
  }, [filter]);

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-col gap-3 border-b border-slate-200 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-semibold text-slate-950">Warren tax-account map</h2>
          <p className="text-sm text-slate-600">Color shows filing and mailing observations, not occupancy.</p>
        </div>
        <label className="text-sm font-medium text-slate-700">
          Filter{" "}
          <select className="ml-2 rounded-md border border-slate-300 bg-white px-2 py-1" value={filter} onChange={(event) => setFilter(event.target.value as Filter)}>
            <option value="all">All mapped accounts</option>
            <option value="homestead">Homestead filed</option>
            <option value="not_homestead">No homestead filing</option>
            <option value="out_of_state">Out-of-state mailing</option>
          </select>
        </label>
      </div>
      <div className="relative h-[520px] bg-slate-100">
        <div ref={container} className="h-full w-full" />
        {status && <p className="absolute inset-0 grid place-items-center p-6 text-center text-slate-600">{status}</p>}
      </div>
      <div className="grid gap-3 border-t border-slate-200 p-5 sm:grid-cols-3">
        <Legend color="bg-emerald-600" label="Homestead filed" />
        <Legend color="bg-amber-600" label="Out-of-state mailing address" />
        <Legend color="bg-slate-500" label="Other or unknown" />
      </div>
      {selected && (
        <div className="border-t border-slate-200 bg-slate-50 p-5 text-sm text-slate-700">
          <p className="font-semibold text-slate-950">{selected.address || "No address in extract"}</p>
          <p className="mt-1">Homestead filed: {selected.homestead_filed === null ? "unknown" : selected.homestead_filed ? "yes" : "no"}</p>
          <p>Mailing state: {selected.mailing_state || "unknown"}</p>
          <p>Housing-unit claims: {selected.housing_unit_claims} ({selected.unit_evidence_levels.join(", ") || "unknown evidence"})</p>
        </div>
      )}
    </section>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return <p className="flex items-center gap-2 text-sm text-slate-600"><span className={`h-3 w-3 rounded-full ${color}`} />{label}</p>;
}
