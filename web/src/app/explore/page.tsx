"use client";

import { CopilotKit, useRenderToolCall } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import { useState, useCallback } from "react";
import ArtifactPanel from "@/components/ArtifactPanel";

export interface Artifact {
  id: string;
  type: "map" | "pie_chart" | "bar_chart" | "table" | "stats" | "property_card" | "property_breakdown" | "dwelling_breakdown" | "dwelling_map";
  title: string;
  data: unknown;
  timestamp: number;
}

interface PropertySummary {
  span: string;
  address: string | null;
  owner: string | null;
  acres: number | null;
  assessed_total: number | null;
  property_type: string | null;
  homestead: boolean;
  lat: number | null;
  lng: number | null;
}

interface PropertyStats {
  total_parcels: number;
  total_value: number;
  avg_value: number;
  homestead_count: number;
  non_homestead_count: number;
  homestead_percent: number;
}

interface PropertyTypeBreakdown {
  property_type: string;
  count: number;
  total_value: number;
  avg_value: number;
}

interface DwellingSummary {
  id: string;
  address: string | null;
  unit_number: string | null;
  bedrooms: number | null;
  tax_classification: string | null;
  use_type: string | null;
  is_str: boolean;
  str_name: string | null;
  str_price_per_night: number | null;
  lat: number | null;
  lng: number | null;
}

interface DwellingBreakdownResult {
  total_dwellings: number;
  homestead_count: number;
  nhs_residential_count: number;
  nhs_nonresidential_count: number;
  str_count: number;
  headline: string;
  use_type_breakdown: Record<string, number>;
}

function ChatWithArtifacts({ onArtifact }: { onArtifact: (artifact: Omit<Artifact, "id" | "timestamp">) => void }) {
  // Helper to defer state updates to avoid React render warnings
  const deferArtifact = useCallback(
    (artifact: Omit<Artifact, "id" | "timestamp">) => {
      queueMicrotask(() => onArtifact(artifact));
    },
    [onArtifact]
  );

  // Register tool renderers for each backend tool
  // These intercept tool call results and create artifacts

  useRenderToolCall({
    name: "get_property_stats",
    description: "Get aggregate statistics about properties",
    render: ({ result, status }) => {
      if (status === "complete" && result) {
        const stats = result as PropertyStats;

        // Create stats artifact
        deferArtifact({
          type: "stats",
          title: "Warren Property Statistics",
          data: {
            cards: [
              { label: "Total Properties", value: stats.total_parcels },
              { label: "Total Assessed Value", value: `$${stats.total_value?.toLocaleString() || 0}` },
              { label: "Average Property Value", value: `$${stats.avg_value?.toLocaleString() || 0}` },
              { label: "Primary Residences", value: `${stats.homestead_count} (${stats.homestead_percent}%)` },
              { label: "Second Homes / Other", value: stats.non_homestead_count },
            ],
          },
        });

        // Create pie chart artifact
        deferArtifact({
          type: "pie_chart",
          title: "Residency Breakdown",
          data: {
            data: [
              { label: "Primary Residence", value: stats.homestead_count, color: "#22c55e" },
              { label: "Second Home / Other", value: stats.non_homestead_count, color: "#f97316" },
            ],
          },
        });
      }
      return <></>; // Don't render inline
    },
  });

  useRenderToolCall({
    name: "search_properties",
    description: "Search for properties",
    render: ({ result, status }) => {
      if (status === "complete" && result) {
        const properties = result as PropertySummary[];
        if (properties.length === 0) return <></>;

        // Create map artifact if properties have coordinates
        const mappable = properties.filter((p) => p.lat && p.lng);
        if (mappable.length > 0) {
          deferArtifact({
            type: "map",
            title: `Found ${properties.length} properties`,
            data: {
              markers: mappable.map((p) => ({
                lat: p.lat,
                lng: p.lng,
                label: p.address || p.span,
                color: p.homestead ? "green" : "orange",
                popup: `<b>${p.address || "No Address"}</b><br/>
                        Owner: ${p.owner || "Unknown"}<br/>
                        Value: ${p.assessed_total ? "$" + p.assessed_total.toLocaleString() : "N/A"}<br/>
                        ${p.homestead ? "Primary Residence" : "Second Home / Other"}`,
              })),
              center: [mappable[0].lat, mappable[0].lng],
              zoom: 14,
            },
          });
        }

        // Create table artifact
        deferArtifact({
          type: "table",
          title: `Property Search Results (${properties.length})`,
          data: {
            columns: ["Address", "Owner", "Value", "Type", "Residence"],
            rows: properties.map((p) => [
              p.address || "-",
              p.owner || "-",
              p.assessed_total ? `$${p.assessed_total.toLocaleString()}` : "-",
              p.property_type || "-",
              p.homestead ? "Primary" : "Second Home",
            ]),
          },
        });
      }
      return <></>;
    },
  });

  useRenderToolCall({
    name: "get_property_type_breakdown",
    description: "Get breakdown by property type",
    render: ({ result, status }) => {
      if (status === "complete" && result) {
        const breakdown = result as PropertyTypeBreakdown[];

        // Create bar chart
        deferArtifact({
          type: "bar_chart",
          title: "Properties by Type",
          data: {
            data: breakdown.map((b) => ({
              label: b.property_type || "Unknown",
              value: b.total_value,
            })),
            xLabel: "Property Type",
            yLabel: "Total Value",
          },
        });

        // Create table
        deferArtifact({
          type: "table",
          title: "Property Type Details",
          data: {
            columns: ["Type", "Count", "Total Value", "Avg Value"],
            rows: breakdown.map((b) => [
              b.property_type || "Unknown",
              b.count,
              `$${b.total_value.toLocaleString()}`,
              `$${b.avg_value.toLocaleString()}`,
            ]),
          },
        });
      }
      return <></>;
    },
  });

  useRenderToolCall({
    name: "get_property_breakdown",
    description: "Get property breakdown by residency category",
    render: ({ result, status }) => {
      if (status === "complete" && result) {
        const breakdown = result as {
          categories: Array<{
            name: string;
            count: number;
            value: number;
            avg_value: number;
            color: string;
            description: string;
          }>;
          total_parcels: number;
          total_value: number;
          headline: string;
          subheadline: string;
        };

        deferArtifact({
          type: "property_breakdown",
          title: breakdown.headline || "Warren Property Breakdown",
          data: {
            categories: breakdown.categories.map((c) => ({
              name: c.name,
              count: c.count,
              value: c.value,
              avgValue: c.avg_value,
              color: c.color,
              description: c.description,
            })),
            totalParcels: breakdown.total_parcels,
            totalValue: breakdown.total_value,
            headline: breakdown.headline,
            subheadline: breakdown.subheadline,
          },
        });
      }
      return <></>;
    },
  });

  useRenderToolCall({
    name: "get_property_by_span",
    description: "Get property by SPAN ID",
    render: ({ result, status }) => {
      if (status === "complete" && result) {
        const property = result as PropertySummary;
        if (!property) return <></>;

        // Create property card
        deferArtifact({
          type: "property_card",
          title: property.address || property.span,
          data: property,
        });

        // Create map with single marker
        if (property.lat && property.lng) {
          deferArtifact({
            type: "map",
            title: property.address || property.span,
            data: {
              markers: [
                {
                  lat: property.lat,
                  lng: property.lng,
                  label: property.address || property.span,
                  color: property.homestead ? "green" : "orange",
                  popup: `<b>${property.address || "No Address"}</b>`,
                },
              ],
              center: [property.lat, property.lng],
              zoom: 16,
            },
          });
        }
      }
      return <></>;
    },
  });

  useRenderToolCall({
    name: "get_dwelling_breakdown",
    description: "Get breakdown of dwellings by Act 73 classification",
    render: ({ result, status }) => {
      if (status === "complete" && result) {
        const breakdown = result as DwellingBreakdownResult;

        // Create dwelling breakdown artifact
        deferArtifact({
          type: "dwelling_breakdown",
          title: breakdown.headline || "Warren Dwelling Breakdown",
          data: breakdown,
        });

        // Create pie chart for tax classifications
        deferArtifact({
          type: "pie_chart",
          title: "Dwelling Tax Classifications (Act 73)",
          data: {
            data: [
              { label: "HOMESTEAD (Primary)", value: breakdown.homestead_count, color: "#22c55e" },
              { label: "NHS_RESIDENTIAL (Second Homes/STR)", value: breakdown.nhs_residential_count, color: "#f97316" },
              { label: "NHS_NONRESIDENTIAL", value: breakdown.nhs_nonresidential_count, color: "#ef4444" },
            ],
          },
        });
      }
      return <></>;
    },
  });

  useRenderToolCall({
    name: "search_dwellings",
    description: "Search dwelling units",
    render: ({ result, status }) => {
      if (status === "complete" && result) {
        const dwellings = result as DwellingSummary[];
        if (dwellings.length === 0) return <></>;

        // Create map artifact if dwellings have coordinates
        const mappable = dwellings.filter((d) => d.lat && d.lng);
        if (mappable.length > 0) {
          deferArtifact({
            type: "dwelling_map",
            title: `Found ${dwellings.length} dwellings`,
            data: {
              markers: mappable.map((d) => ({
                lat: d.lat,
                lng: d.lng,
                label: d.address || "Unknown",
                // Color by tax classification: green=HOMESTEAD, orange=NHS_RESIDENTIAL, red=NHS_NONRESIDENTIAL
                color: d.tax_classification === "HOMESTEAD" ? "green"
                  : d.tax_classification === "NHS_RESIDENTIAL" ? "orange"
                  : "red",
                isStr: d.is_str,
                popup: `<b>${d.address || "No Address"}</b>${d.unit_number ? ` (${d.unit_number})` : ""}<br/>
                        Class: ${d.tax_classification || "Unknown"}<br/>
                        Use: ${d.use_type || "Unknown"}<br/>
                        ${d.is_str ? `<b>STR:</b> ${d.str_name || "Unnamed"}<br/>$${(d.str_price_per_night || 0) / 100}/night` : ""}`,
              })),
              center: [mappable[0].lat, mappable[0].lng],
              zoom: 14,
            },
          });
        }

        // Create table artifact
        deferArtifact({
          type: "table",
          title: `Dwelling Search Results (${dwellings.length})`,
          data: {
            columns: ["Address", "Unit", "Classification", "Use", "STR", "Beds"],
            rows: dwellings.map((d) => [
              d.address || "-",
              d.unit_number || "-",
              d.tax_classification || "-",
              d.use_type || "-",
              d.is_str ? "Y" : "-",
              d.bedrooms || "-",
            ]),
          },
        });
      }
      return <></>;
    },
  });

  return (
    <CopilotChat
      className="h-full"
      labels={{
        title: "Warren Community Assistant",
        initial: "Ask me about Warren, VT! Try: \"Show dwelling breakdown\" or \"Show me STR dwellings\" or \"Search properties on Main Street\"",
      }}
    />
  );
}

export default function ExplorePage() {
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);

  const addArtifact = useCallback((artifact: Omit<Artifact, "id" | "timestamp">) => {
    setArtifacts((prev) => [
      ...prev,
      {
        ...artifact,
        id: `artifact-${Date.now()}-${Math.random().toString(36).slice(2)}`,
        timestamp: Date.now(),
      },
    ]);
  }, []);

  return (
    <CopilotKit runtimeUrl="http://localhost:8999/awp">
      <div className="flex h-screen bg-gray-100">
        {/* Chat Panel - Left Side */}
        <div className="w-2/5 border-r border-gray-200 bg-white flex flex-col">
          <header className="p-4 border-b border-gray-200">
            <h1 className="text-xl font-semibold text-gray-800">Open Valley</h1>
            <p className="text-sm text-gray-500">Warren Community Intelligence</p>
          </header>
          <div className="flex-1 overflow-hidden">
            <ChatWithArtifacts onArtifact={addArtifact} />
          </div>
        </div>

        {/* Artifact Panel - Right Side */}
        <div className="w-3/5 bg-gray-50">
          <ArtifactPanel artifacts={artifacts} onAddArtifact={addArtifact} />
        </div>
      </div>
    </CopilotKit>
  );
}
