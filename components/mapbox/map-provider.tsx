"use client"

import type React from "react"
import { useEffect, useRef, useState } from "react"
import mapboxgl from "mapbox-gl"
import "mapbox-gl/dist/mapbox-gl.css"
import { MapContext } from "./map-context"

// Warren, VT coordinates
const WARREN_CENTER = [-72.8648, 44.1159]

const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || "pk.eyJ1IjoidGVzdCIsImEiOiJjbGV0ZXN0In0.test"
mapboxgl.accessToken = MAPBOX_TOKEN

type MapProviderProps = {
  mapContainerRef: React.RefObject<HTMLDivElement>
  initialViewState?: {
    longitude: number
    latitude: number
    zoom: number
  }
  children?: React.ReactNode
}

export default function MapProvider({
  mapContainerRef,
  initialViewState = {
    longitude: WARREN_CENTER[0],
    latitude: WARREN_CENTER[1],
    zoom: 12,
  },
  children,
}: MapProviderProps) {
  const map = useRef<mapboxgl.Map | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!mapContainerRef.current || map.current) return

    if (!process.env.NEXT_PUBLIC_MAPBOX_TOKEN) {
      setError("Mapbox token not configured. Please add NEXT_PUBLIC_MAPBOX_TOKEN to your environment variables.")
      return
    }

    try {
      map.current = new mapboxgl.Map({
        container: mapContainerRef.current,
        style: "mapbox://styles/mapbox/outdoors-v12", // Great for Vermont terrain
        center: [initialViewState.longitude, initialViewState.latitude],
        zoom: initialViewState.zoom,
        attributionControl: false,
        logoPosition: "bottom-right",
      })

      map.current.on("load", () => {
        setLoaded(true)

        // Sample property data around Warren, VT with more realistic locations
        const sampleProperties = [
          {
            lng: -72.8648,
            lat: 44.1159,
            type: "primary",
            price: "$485,000",
            address: "100 Main St",
            owner: "Smith Family",
          },
          {
            lng: -72.87,
            lat: 44.12,
            type: "secondary",
            price: "$650,000",
            address: "25 Mountain View Rd",
            owner: "Johnson Trust",
          },
          {
            lng: -72.86,
            lat: 44.11,
            type: "rental",
            price: "$420,000",
            address: "15 Valley Rd",
            owner: "Valley Properties LLC",
          },
          {
            lng: -72.875,
            lat: 44.125,
            type: "primary",
            price: "$520,000",
            address: "8 Brook Rd",
            owner: "Williams Family",
          },
          {
            lng: -72.855,
            lat: 44.105,
            type: "secondary",
            price: "$780,000",
            address: "42 Ski Hill Rd",
            owner: "Mountain Retreat Inc",
          },
          {
            lng: -72.868,
            lat: 44.118,
            type: "primary",
            price: "$395,000",
            address: "33 Village Green",
            owner: "Davis Family",
          },
          {
            lng: -72.872,
            lat: 44.108,
            type: "secondary",
            price: "$725,000",
            address: "18 Ridge View Dr",
            owner: "Boston Holdings",
          },
          {
            lng: -72.858,
            lat: 44.122,
            type: "rental",
            price: "$380,000",
            address: "7 River Bend Ln",
            owner: "Mad River Rentals",
          },
        ]

        sampleProperties.forEach((property) => {
          const color = property.type === "primary" ? "#10b981" : property.type === "secondary" ? "#3b82f6" : "#f59e0b"

          const popup = new mapboxgl.Popup({ offset: 25 }).setHTML(`
            <div class="p-3 min-w-[200px]">
              <h3 class="font-semibold text-lg mb-1">${property.address}</h3>
              <div class="space-y-1">
                <p class="text-sm"><span class="font-medium">Type:</span> ${property.type.charAt(0).toUpperCase() + property.type.slice(1)} residence</p>
                <p class="text-sm"><span class="font-medium">Owner:</span> ${property.owner}</p>
                <p class="text-lg font-bold text-green-600">${property.price}</p>
              </div>
            </div>
          `)

          const markerElement = document.createElement("div")
          markerElement.className = "custom-marker"
          markerElement.style.cssText = `
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background-color: ${color};
            border: 3px solid white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            cursor: pointer;
            animation: pulse 2s infinite;
          `

          new mapboxgl.Marker({ element: markerElement })
            .setLngLat([property.lng, property.lat])
            .setPopup(popup)
            .addTo(map.current!)
        })

        map.current!.addSource("mapbox-dem", {
          type: "raster-dem",
          url: "mapbox://mapbox.mapbox-terrain-dem-v1",
          tileSize: 512,
          maxzoom: 14,
        })

        map.current!.setTerrain({ source: "mapbox-dem", exaggeration: 1.5 })
      })

      map.current.on("error", (e) => {
        console.error("Mapbox error:", e)
        setError("Failed to load map. Please check your Mapbox token.")
      })
    } catch (err) {
      console.error("Error initializing map:", err)
      setError("Failed to initialize map.")
    }

    return () => {
      if (map.current) {
        map.current.remove()
        map.current = null
      }
    }
  }, [initialViewState, mapContainerRef])

  if (error) {
    return (
      <div className="absolute inset-0 flex items-center justify-center bg-muted rounded-lg">
        <div className="text-center p-6">
          <div className="text-red-500 mb-2">⚠️</div>
          <p className="text-sm text-muted-foreground mb-2">Map Error</p>
          <p className="text-xs text-muted-foreground max-w-xs">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <MapContext.Provider value={{ map: map.current }}>
      {children}
      {!loaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-muted rounded-lg">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-2"></div>
            <p className="text-sm text-muted-foreground">Loading Warren, VT map...</p>
          </div>
        </div>
      )}
    </MapContext.Provider>
  )
}
