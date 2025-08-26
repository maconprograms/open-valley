"use client"

import type React from "react"
import { useEffect, useRef, useState } from "react"
import mapboxgl from "mapbox-gl"
import "mapbox-gl/dist/mapbox-gl.css"
import { MapContext } from "./map-context"

// Warren, VT coordinates
const WARREN_CENTER = [-72.8648, 44.1159]

mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || ""

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

  useEffect(() => {
    if (!mapContainerRef.current || map.current) return

    map.current = new mapboxgl.Map({
      container: mapContainerRef.current,
      style: "mapbox://styles/mapbox/outdoors-v12", // Great for Vermont terrain
      center: [initialViewState.longitude, initialViewState.latitude],
      zoom: initialViewState.zoom,
      attributionControl: false,
      logoPosition: "bottom-right",
    })

    // Add sample property markers for Warren, VT
    map.current.on("load", () => {
      setLoaded(true)

      // Sample property data around Warren
      const sampleProperties = [
        { lng: -72.8648, lat: 44.1159, type: "primary", price: "$485,000", address: "Main St" },
        { lng: -72.87, lat: 44.12, type: "secondary", price: "$650,000", address: "Mountain View Rd" },
        { lng: -72.86, lat: 44.11, type: "rental", price: "$420,000", address: "Valley Rd" },
        { lng: -72.875, lat: 44.125, type: "primary", price: "$520,000", address: "Brook Rd" },
        { lng: -72.855, lat: 44.105, type: "secondary", price: "$780,000", address: "Ski Hill Rd" },
      ]

      sampleProperties.forEach((property) => {
        const color = property.type === "primary" ? "#10b981" : property.type === "secondary" ? "#3b82f6" : "#f59e0b"

        const popup = new mapboxgl.Popup({ offset: 25 }).setHTML(`
          <div class="p-2">
            <h3 class="font-semibold">${property.address}</h3>
            <p class="text-sm text-gray-600">${property.type} residence</p>
            <p class="font-medium">${property.price}</p>
          </div>
        `)

        new mapboxgl.Marker({ color }).setLngLat([property.lng, property.lat]).setPopup(popup).addTo(map.current!)
      })
    })

    return () => {
      if (map.current) {
        map.current.remove()
        map.current = null
      }
    }
  }, [initialViewState, mapContainerRef])

  return (
    <MapContext.Provider value={{ map: map.current }}>
      {children}
      {!loaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-muted">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-2"></div>
            <p className="text-sm text-muted-foreground">Loading Warren, VT map...</p>
          </div>
        </div>
      )}
    </MapContext.Provider>
  )
}
