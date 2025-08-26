"use client"

import { createContext, useContext } from "react"
import type mapboxgl from "mapbox-gl"

interface MapContextType {
  map: mapboxgl.Map | null
}

export const MapContext = createContext<MapContextType | null>(null)

export function useMap() {
  const context = useContext(MapContext)
  if (!context) {
    throw new Error("useMap must be used within a MapProvider")
  }
  return context
}
