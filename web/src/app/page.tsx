"use client";

import { CopilotKit, useRenderToolCall } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import { useState, useCallback } from "react";
import ArtifactPanel from "@/components/ArtifactPanel";

export interface Artifact {
  id: string;
  type: "map" | "pie_chart" | "bar_chart" | "table" | "stats" | "property_card";
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
      return null; // Don't render inline
    },
  });

  useRenderToolCall({
    name: "search_properties",
    description: "Search for properties",
    render: ({ result, status }) => {
      if (status === "complete" && result) {
        const properties = result as PropertySummary[];
        if (properties.length === 0) return null;

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
      return null;
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
      return null;
    },
  });

  useRenderToolCall({
    name: "get_property_by_span",
    description: "Get property by SPAN ID",
    render: ({ result, status }) => {
      if (status === "complete" && result) {
        const property = result as PropertySummary;
        if (!property) return null;

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
      return null;
    },
  });

  return (
    <CopilotChat
      className="h-full"
      labels={{
        title: "Warren Property Assistant",
        initial: "Ask me about properties in Warren, VT! Try: \"How many properties are in Warren?\" or \"Show me properties on Woods Road\"",
      }}
    />
  );
}

export default function Home() {
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
    <CopilotKit runtimeUrl="http://localhost:8000/awp">
      <div className="flex h-screen bg-gray-100">
        {/* Chat Panel - Left Side */}
        <div className="w-2/5 border-r border-gray-200 bg-white flex flex-col">
          <header className="p-4 border-b border-gray-200">
            <h1 className="text-xl font-semibold text-gray-800">Open Valley</h1>
            <p className="text-sm text-gray-500">Warren Property Intelligence</p>
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
