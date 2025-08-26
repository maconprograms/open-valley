"use client"

import { useEffect, useRef } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { MapPin, Layers, Home, Info } from "lucide-react"

// Sample property data for Warren, VT
const sampleProperties = [
  { id: 1, lat: 44.1159, lng: -72.8648, address: "123 Main St", type: "Single Family", use: "Primary", value: 485000 },
  { id: 2, lat: 44.1145, lng: -72.8632, address: "456 Valley Rd", type: "Condo", use: "Secondary", value: 320000 },
  {
    id: 3,
    lat: 44.1172,
    lng: -72.8665,
    address: "789 Mountain View Dr",
    type: "Single Family",
    use: "Rental",
    value: 650000,
  },
  { id: 4, lat: 44.1138, lng: -72.8621, address: "321 Brook Ln", type: "Single Family", use: "Primary", value: 425000 },
  { id: 5, lat: 44.1165, lng: -72.8655, address: "654 Ski Trail Rd", type: "Condo", use: "Secondary", value: 380000 },
]

export default function WarrenMap() {
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<any>(null)

  useEffect(() => {
    if (typeof window === "undefined" || !mapRef.current) return

    // Dynamically import Leaflet to avoid SSR issues
    const initMap = async () => {
      const L = (await import("leaflet")).default

      // Fix for default markers in Next.js
      delete (L.Icon.Default.prototype as any)._getIconUrl
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png",
        iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
        shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
      })

      // Initialize map centered on Warren, VT
      const map = L.map(mapRef.current!).setView([44.1159, -72.8648], 14)

      // Add OpenStreetMap tiles
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 18,
      }).addTo(map)

      // Add terrain layer option
      const terrainLayer = L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {
        attribution:
          'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)',
        maxZoom: 17,
      })

      // Layer control
      const baseMaps = {
        "Street Map": L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        }),
        Terrain: terrainLayer,
      }

      L.control.layers(baseMaps).addTo(map)

      // Custom icons for different property types
      const getPropertyIcon = (use: string) => {
        const colors = {
          Primary: "#22c55e",
          Secondary: "#3b82f6",
          Rental: "#f59e0b",
        }

        return L.divIcon({
          html: `<div style="background-color: ${colors[use as keyof typeof colors] || "#6b7280"}; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`,
          className: "custom-marker",
          iconSize: [16, 16],
          iconAnchor: [8, 8],
        })
      }

      // Add property markers
      sampleProperties.forEach((property) => {
        const marker = L.marker([property.lat, property.lng], {
          icon: getPropertyIcon(property.use),
        }).addTo(map)

        // Popup with property details
        marker.bindPopup(`
          <div class="p-2">
            <h3 class="font-semibold text-sm">${property.address}</h3>
            <p class="text-xs text-gray-600">${property.type}</p>
            <p class="text-xs"><span class="font-medium">Use:</span> ${property.use}</p>
            <p class="text-xs"><span class="font-medium">Value:</span> $${property.value.toLocaleString()}</p>
          </div>
        `)
      })

      // Add Warren town boundary (approximate)
      const warrenBounds = [
        [44.105, -72.88],
        [44.105, -72.85],
        [44.125, -72.85],
        [44.125, -72.88],
        [44.105, -72.88],
      ]

      L.polygon(warrenBounds, {
        color: "#0ea5e9",
        weight: 2,
        opacity: 0.8,
        fillColor: "#0ea5e9",
        fillOpacity: 0.1,
      })
        .addTo(map)
        .bindPopup("Warren, VT Town Boundary")

      mapInstanceRef.current = map
    }

    initMap()

    // Cleanup
    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
        mapInstanceRef.current = null
      }
    }
  }, [])

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-lg">
              <MapPin className="h-5 w-5 text-primary" />
              Mad River Valley Interactive Map
            </CardTitle>
            <CardDescription className="text-sm">Explore Warren, VT properties and surrounding areas</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm">
              <Layers className="h-4 w-4 mr-2" />
              Layers
            </Button>
            <Button variant="outline" size="sm">
              <Info className="h-4 w-4 mr-2" />
              Legend
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col">
        <div className="space-y-3 flex-1 flex flex-col">
          {/* Map Legend */}
          <div className="flex flex-wrap gap-3 p-2 bg-muted rounded-lg">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500 border-2 border-white shadow-sm"></div>
              <span className="text-xs font-medium">Primary Residence</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-blue-500 border-2 border-white shadow-sm"></div>
              <span className="text-xs font-medium">Secondary Home</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-amber-500 border-2 border-white shadow-sm"></div>
              <span className="text-xs font-medium">Rental Property</span>
            </div>
          </div>

          {/* Map Container */}
          <div className="relative flex-1">
            <div ref={mapRef} className="h-full w-full rounded-lg border overflow-hidden" style={{ zIndex: 1 }} />

            {/* Loading overlay - will be hidden once map loads */}
            <div className="absolute inset-0 bg-gradient-to-br from-green-50 to-blue-50 rounded-lg flex items-center justify-center">
              <div className="text-center space-y-4">
                <MapPin className="h-12 w-12 text-primary mx-auto animate-pulse" />
                <div>
                  <h3 className="text-lg font-semibold text-foreground">Loading Interactive Map...</h3>
                  <p className="text-sm text-muted-foreground">Initializing Warren, VT property data</p>
                </div>
              </div>
            </div>
          </div>

          {/* Map Features */}
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline" className="text-xs">
              <Home className="h-3 w-3 mr-1" />
              {sampleProperties.length} Properties
            </Badge>
            <Badge variant="outline" className="text-xs">
              Property Boundaries
            </Badge>
            <Badge variant="outline" className="text-xs">
              Transfer History
            </Badge>
            <Badge variant="outline" className="text-xs">
              Zoning Layers
            </Badge>
            <Badge variant="outline" className="text-xs">
              Terrain View
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
