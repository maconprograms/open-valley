"use client"

import { useRef } from "react"
import MapProvider from "./mapbox/map-provider"
import MapControls from "./mapbox/map-controls"

export default function WarrenMapbox() {
  const mapContainerRef = useRef<HTMLDivElement>(null)

  return (
    <div className="relative w-full h-full rounded-lg overflow-hidden border">
      <div ref={mapContainerRef} className="w-full h-full" />
      <MapProvider mapContainerRef={mapContainerRef}>
        <MapControls />
      </MapProvider>
    </div>
  )
}
