"use client";

import { useEffect, useRef, useState } from "react";

interface MapMarker {
  lat: number;
  lng: number;
  label?: string;
  color?: string;
  popup?: string;
}

interface MapData {
  markers?: MapMarker[];
  center?: [number, number];
  zoom?: number;
}

interface MapArtifactProps {
  data: unknown;
}

// Default center: Warren, VT
const WARREN_CENTER: [number, number] = [44.1167, -72.8653];
const DEFAULT_ZOOM = 13;

export default function MapArtifact({ data }: MapArtifactProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  useEffect(() => {
    if (!isClient || !mapContainer.current || mapRef.current) return;

    // Dynamic import of Leaflet to avoid SSR issues
    import("leaflet").then((L) => {
      // Import CSS dynamically too
      import("leaflet/dist/leaflet.css");

      const mapData = data as MapData;
      const center = mapData?.center || WARREN_CENTER;
      const zoom = mapData?.zoom || DEFAULT_ZOOM;

      // Initialize map
      const map = L.map(mapContainer.current!).setView(center, zoom);
      mapRef.current = map;

      // Add OpenStreetMap tiles
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      }).addTo(map);

      // Add markers
      if (mapData?.markers) {
        mapData.markers.forEach((marker) => {
          const color = marker.color === "green" ? "#22c55e" : "#f97316";

          const icon = L.divIcon({
            className: "custom-marker",
            html: `<div style="
              width: 24px;
              height: 24px;
              background: ${color};
              border: 3px solid white;
              border-radius: 50%;
              box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            "></div>`,
            iconSize: [24, 24],
            iconAnchor: [12, 12],
          });

          const m = L.marker([marker.lat, marker.lng], { icon }).addTo(map);

          if (marker.popup || marker.label) {
            m.bindPopup(marker.popup || marker.label || "");
          }
        });

        // Fit bounds to show all markers
        if (mapData.markers.length > 1) {
          const bounds = L.latLngBounds(
            mapData.markers.map((m) => [m.lat, m.lng] as [number, number])
          );
          map.fitBounds(bounds, { padding: [50, 50] });
        }
      }
    });

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, [isClient, data]);

  if (!isClient) {
    return (
      <div className="h-96 rounded-lg bg-gray-100 flex items-center justify-center">
        <span className="text-gray-500">Loading map...</span>
      </div>
    );
  }

  return (
    <div className="h-96 rounded-lg overflow-hidden border border-gray-200 shadow-sm">
      <div ref={mapContainer} className="h-full w-full" />
    </div>
  );
}

// TypeScript declaration for Leaflet types
declare global {
  namespace L {
    interface Map {
      remove(): void;
      setView(center: [number, number], zoom: number): Map;
      fitBounds(bounds: LatLngBounds, options?: { padding?: [number, number] }): Map;
    }
    interface LatLngBounds {}
    function map(element: HTMLElement): Map;
    function tileLayer(url: string, options: { attribution: string }): { addTo(map: Map): void };
    function marker(coords: [number, number], options?: { icon?: Icon }): {
      addTo(map: Map): { bindPopup(content: string): void };
    };
    function divIcon(options: {
      className: string;
      html: string;
      iconSize: [number, number];
      iconAnchor: [number, number];
    }): Icon;
    function latLngBounds(coords: [number, number][]): LatLngBounds;
    interface Icon {}
  }
}
