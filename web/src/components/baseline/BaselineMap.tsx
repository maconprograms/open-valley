"use client";

import { useEffect, useRef, useState } from "react";

import { normalizeSelectedParcel, parcelSummaryLines, type SelectedParcel } from "./mapProperties";

type Filter = "all" | "homestead_filed" | "non_homestead" | "unknown";

const mapFilters: Record<Filter, unknown[] | null> = {
  all: null,
  homestead_filed: ["==", ["get", "tax_status_bucket"], "homestead_filed"],
  non_homestead: ["==", ["get", "tax_status_bucket"], "non_homestead"],
  unknown: ["==", ["get", "tax_status_bucket"], "unknown"],
};

function applyFilter(map: import("maplibre-gl").Map, filter: Filter) {
  map.setFilter("baseline-parcels-fill", mapFilters[filter] as never);
  map.setFilter("baseline-parcels-line", mapFilters[filter] as never);
}

function tooltipContent(parcel: SelectedParcel): HTMLDivElement {
  const content = document.createElement("div");
  content.className = "text-sm leading-5 text-slate-700";
  for (const [index, line] of parcelSummaryLines(parcel).entries()) {
    const row = document.createElement("p");
    row.textContent = line;
    if (index === 0) row.className = "font-semibold text-slate-950";
    content.append(row);
  }
  return content;
}

export default function BaselineMap({ apiBase }: { apiBase: string }) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<import("maplibre-gl").Map | null>(null);
  const filterRef = useRef<Filter>("all");
  const [filter, setFilter] = useState<Filter>("all");
  const [selected, setSelected] = useState<SelectedParcel | null>(null);
  const [status, setStatus] = useState("Loading parcel map…");

  useEffect(() => {
    if (!container.current || mapRef.current) return;
    let destroyed = false;
    const controller = new AbortController();
    void (async () => {
      try {
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
            const response = await fetch(`${apiBase}/api/baseline/map`, { signal: controller.signal });
            if (!response.ok) throw new Error(`Map API returned ${response.status}`);
            const data = await response.json();
            if (destroyed) return;
            map.addSource("baseline-parcels", { type: "geojson", data });
            map.addLayer({
              id: "baseline-parcels-fill",
              type: "fill",
              source: "baseline-parcels",
              paint: {
                "fill-color": [
                  "case",
                  ["==", ["get", "tax_status_bucket"], "homestead_filed"], "#059669",
                  ["==", ["get", "tax_status_bucket"], "non_homestead"], "#d97706",
                  "#94a3b8",
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
            applyFilter(map, filterRef.current);
            const hoverPopup = new maplibregl.Popup({
              closeButton: false,
              closeOnClick: false,
              offset: 10,
            });
            map.on("click", "baseline-parcels-fill", (event) => {
              setSelected(normalizeSelectedParcel(event.features?.[0]?.properties));
            });
            map.on("mousemove", "baseline-parcels-fill", (event) => {
              const parcel = normalizeSelectedParcel(event.features?.[0]?.properties);
              if (!parcel) return;
              hoverPopup.setLngLat(event.lngLat).setDOMContent(tooltipContent(parcel)).addTo(map);
            });
            map.on("mouseenter", "baseline-parcels-fill", () => { map.getCanvas().style.cursor = "pointer"; });
            map.on("mouseleave", "baseline-parcels-fill", () => {
              map.getCanvas().style.cursor = "";
              hoverPopup.remove();
            });
            setStatus("");
          } catch (error) {
            if (!destroyed && !(error instanceof DOMException && error.name === "AbortError")) {
              setStatus("Map data could not be loaded. No substitute map is shown.");
            }
          }
        });
      } catch {
        if (!destroyed) setStatus("Map could not be initialized. No substitute map is shown.");
      }
    })();
    return () => {
      destroyed = true;
      controller.abort();
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, [apiBase]);

  useEffect(() => {
    filterRef.current = filter;
    const map = mapRef.current;
    if (!map?.getLayer("baseline-parcels-fill")) return;
    applyFilter(map, filter);
  }, [filter]);

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-col gap-3 border-b border-slate-200 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-semibold text-slate-950">Warren tax-account map</h2>
          <p className="text-sm text-slate-600">Color shows the source tax-status observation, not occupancy.</p>
        </div>
        <label className="text-sm font-medium text-slate-700">
          Filter{" "}
          <select className="ml-2 rounded-md border border-slate-300 bg-white px-2 py-1" value={filter} onChange={(event) => {
            const nextFilter = event.target.value as Filter;
            filterRef.current = nextFilter;
            setSelected(null);
            setFilter(nextFilter);
          }}>
            <option value="all">All mapped accounts</option>
            <option value="homestead_filed">Homestead filed</option>
            <option value="non_homestead">Non-homestead</option>
            <option value="unknown">Unknown status</option>
          </select>
        </label>
      </div>
      <div className="relative h-[520px] bg-slate-100">
        <div ref={container} className="h-full w-full" />
        {status && <p role="status" className="absolute inset-0 grid place-items-center p-6 text-center text-slate-600">{status}</p>}
      </div>
      <div className="grid gap-3 border-t border-slate-200 p-5 sm:grid-cols-3">
        <Legend color="bg-emerald-600" label="Homestead filed" />
        <Legend color="bg-amber-600" label="Non-homestead" />
        <Legend color="bg-slate-400" label="Unknown status" />
      </div>
      {selected && (
        <div className="border-t border-slate-200 bg-slate-50 p-5 text-sm text-slate-700">
          <p className="font-semibold text-slate-950">{selected.address || "No address in extract"}</p>
          <p className="mt-1">Tax status: {selected.taxStatusBucket === "homestead_filed" ? "Homestead filed" : selected.taxStatusBucket === "non_homestead" ? "Non-homestead" : "Unknown"}</p>
          <p>Housing-unit claims: {selected.housingUnitClaims ?? "unknown"} ({selected.unitEvidenceLevels.join(", ") || "unknown evidence"})</p>
        </div>
      )}
    </section>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return <p className="flex items-center gap-2 text-sm text-slate-600"><span className={`h-3 w-3 rounded-full ${color}`} />{label}</p>;
}
