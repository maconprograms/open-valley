"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";

interface WarrenMapProps {
  homesteadPercent: number;
  secondHomePercent: number;
  homesteadCount: number;
  secondHomeCount: number;
  strCount: number;
}

export default function WarrenMap({
  homesteadPercent,
  secondHomePercent,
  homesteadCount,
  secondHomeCount,
  strCount,
}: WarrenMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const map = useRef<any>(null);
  const [isClient, setIsClient] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setIsClient(true);
  }, []);

  useEffect(() => {
    if (!isClient || !mapContainer.current || map.current) return;

    const initMap = async () => {
      try {
        // Dynamic import for SSR safety
        const maplibregl = await import("maplibre-gl");
        await import("maplibre-gl/dist/maplibre-gl.css");

        const MAPTILER_KEY = process.env.NEXT_PUBLIC_MAPTILER_KEY;

        if (!MAPTILER_KEY) {
          setError("MapTiler API key not configured");
          setIsLoading(false);
          return;
        }

        map.current = new maplibregl.Map({
          container: mapContainer.current!,
          style: `https://api.maptiler.com/maps/outdoor-v2/style.json?key=${MAPTILER_KEY}`,
          center: [-72.85, 44.12], // Warren, VT
          zoom: 12.5,
          pitch: 50, // 3D tilt
          bearing: -20, // Slight rotation
          maxPitch: 85,
        });

        map.current.on("load", async () => {
          // Add terrain source for 3D
          map.current.addSource("terrain", {
            type: "raster-dem",
            url: `https://api.maptiler.com/tiles/terrain-rgb-v2/tiles.json?key=${MAPTILER_KEY}`,
            tileSize: 256,
          });

          // Enable 3D terrain
          map.current.setTerrain({
            source: "terrain",
            exaggeration: 1.5,
          });

          // Fetch and add parcel GeoJSON
          try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8999";
            const response = await fetch(`${apiUrl}/api/parcels/geojson`);
            if (!response.ok) throw new Error("Failed to fetch parcels");
            const geojson = await response.json();

            map.current.addSource("parcels", {
              type: "geojson",
              data: geojson,
            });

            // Choropleth fill layer
            map.current.addLayer({
              id: "parcels-fill",
              type: "fill",
              source: "parcels",
              paint: {
                "fill-color": [
                  "case",
                  ["==", ["get", "classification"], "homestead"],
                  "#22c55e", // green for homestead
                  "#f97316", // orange for second homes
                ],
                "fill-opacity": 0.6,
              },
            });

            // Parcel outlines
            map.current.addLayer({
              id: "parcels-outline",
              type: "line",
              source: "parcels",
              paint: {
                "line-color": "#1e293b",
                "line-width": 0.5,
              },
            });

            // Popup on click
            map.current.on("click", "parcels-fill", (e: { features?: Array<{ properties?: Record<string, unknown> }>; lngLat?: { lng: number; lat: number } }) => {
              if (!e.features?.length) return;
              const props = e.features[0].properties;
              if (!props) return;

              const address = props.E911ADDR || "Unknown";
              const owner = props.OWNER1 || "Unknown";
              const value = props.REAL_FLV
                ? `$${Number(props.REAL_FLV).toLocaleString()}`
                : "N/A";
              const status = props.classification === "homestead"
                ? '<span style="color: #22c55e;">Primary Residence</span>'
                : '<span style="color: #f97316;">Second Home</span>';

              new maplibregl.Popup()
                .setLngLat(e.lngLat!)
                .setHTML(`
                  <div style="font-family: system-ui; font-size: 13px;">
                    <strong style="font-size: 14px;">${address}</strong><br/>
                    <span style="color: #666;">${owner}</span><br/>
                    <div style="margin-top: 4px;">
                      ${status}<br/>
                      Value: ${value}
                    </div>
                  </div>
                `)
                .addTo(map.current);
            });

            // Change cursor on hover
            map.current.on("mouseenter", "parcels-fill", () => {
              map.current.getCanvas().style.cursor = "pointer";
            });
            map.current.on("mouseleave", "parcels-fill", () => {
              map.current.getCanvas().style.cursor = "";
            });
          } catch (err) {
            console.error("Failed to load parcels:", err);
          }

          setIsLoading(false);
        });

        // Add navigation controls
        map.current.addControl(
          new maplibregl.NavigationControl({ visualizePitch: true }),
          "top-right"
        );
      } catch (err) {
        console.error("Map initialization error:", err);
        setError("Failed to initialize map");
        setIsLoading(false);
      }
    };

    initMap();

    return () => {
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, [isClient]);

  if (!isClient) {
    return (
      <div className="relative h-[1000px] rounded-2xl bg-slate-800 flex items-center justify-center">
        <span className="text-slate-400">Loading 3D map...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="relative h-[1000px] rounded-2xl bg-slate-800 flex items-center justify-center">
        <span className="text-red-400">{error}</span>
      </div>
    );
  }

  return (
    <div className="relative h-[1000px] rounded-2xl overflow-hidden">
      <div ref={mapContainer} className="h-full w-full" />

      {/* Loading overlay */}
      {isLoading && (
        <div className="absolute inset-0 bg-slate-900/80 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-green-400 mx-auto mb-3"></div>
            <span className="text-slate-300">Loading 3D terrain...</span>
          </div>
        </div>
      )}

      {/* Stats overlay - top left */}
      <div className="absolute top-4 left-4 bg-slate-900/90 backdrop-blur-sm px-5 py-4 rounded-xl text-white max-w-xs">
        <p className="text-green-400 font-medium uppercase tracking-wider text-xs mb-1">
          Warren, Vermont
        </p>
        <h2 className="text-2xl font-bold leading-tight">
          <span className="text-green-400">{homesteadPercent}%</span> Primary
          <br />
          <span className="text-orange-400">{secondHomePercent}%</span> Second Homes
        </h2>
        <p className="text-slate-400 text-sm mt-2">
          Explore how Vermont&apos;s Act 73 dwelling classifications will reshape
          property taxation in our mountain community.
        </p>
      </div>

      {/* Legend - bottom left */}
      <div className="absolute bottom-4 left-4 bg-slate-900/90 backdrop-blur-sm px-4 py-3 rounded-lg text-white">
        <div className="flex gap-6 text-sm">
          <div className="flex items-center gap-2">
            <span className="w-4 h-4 rounded bg-green-500" />
            <span>Homestead ({homesteadCount.toLocaleString()})</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-4 rounded bg-orange-500" />
            <span>Second Home ({secondHomeCount.toLocaleString()})</span>
          </div>
        </div>
      </div>

      {/* STR callout - bottom right */}
      {strCount > 0 && (
        <div className="absolute bottom-4 right-4 bg-slate-900/90 backdrop-blur-sm px-4 py-2 rounded-lg">
          <span className="text-red-400 font-bold text-xl">{strCount}</span>
          <span className="text-slate-300 ml-2">Active STR listings</span>
        </div>
      )}

      {/* Action buttons - top right (below nav controls) */}
      <div className="absolute top-20 right-4 flex flex-col gap-2">
        <Link
          href="/explore"
          className="flex items-center gap-2 bg-green-600 hover:bg-green-500 text-white px-4 py-2 rounded-lg font-medium transition-colors text-sm shadow-lg"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          Explore with AI
        </Link>
        <a
          href="https://legislature.vermont.gov/bill/status/2026/H.454"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg font-medium transition-colors text-sm shadow-lg"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
          Learn About Act 73
        </a>
      </div>
    </div>
  );
}
