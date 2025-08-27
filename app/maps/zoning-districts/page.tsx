import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { WarrenMapbox } from "@/components/warren-mapbox"
import { MapProvider } from "@/components/mapbox/map-provider"
import { Map, Building2, Trees, Factory } from "lucide-react"

export default function ZoningDistrictsMap() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold text-balance">Zoning Districts Map</h1>
        <p className="text-lg text-muted-foreground text-pretty">
          Explore zoning classifications, permitted uses, and regulatory boundaries across communities.
        </p>
      </div>

      {/* Zoning Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Residential Zones</CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">12</div>
            <p className="text-xs text-muted-foreground">Districts</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Conservation Areas</CardTitle>
            <Trees className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">8</div>
            <p className="text-xs text-muted-foreground">Protected zones</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Commercial Zones</CardTitle>
            <Factory className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">5</div>
            <p className="text-xs text-muted-foreground">Business districts</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Districts</CardTitle>
            <Map className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">25</div>
            <p className="text-xs text-muted-foreground">All zones</p>
          </CardContent>
        </Card>
      </div>

      {/* Map */}
      <Card className="h-[600px]">
        <CardHeader>
          <CardTitle>Zoning Classification Map</CardTitle>
          <CardDescription>Color-coded districts showing permitted uses and development regulations</CardDescription>
        </CardHeader>
        <CardContent className="h-[calc(100%-100px)]">
          <MapProvider>
            <WarrenMapbox />
          </MapProvider>
        </CardContent>
      </Card>
    </div>
  )
}
