import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { WarrenMapbox } from "@/components/warren-mapbox"
import { MapProvider } from "@/components/mapbox/map-provider"
import { Home, TrendingUp, Users, Building } from "lucide-react"

export default function PropertyOverviewMap() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold text-balance">Property Overview Map</h1>
        <p className="text-lg text-muted-foreground text-pretty">
          Interactive map showing all parcels, ownership data, and property classifications across the Mad River Valley.
        </p>
      </div>

      {/* Key Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Parcels</CardTitle>
            <Building className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">1,247</div>
            <p className="text-xs text-muted-foreground">Across all communities</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Homestead Properties</CardTitle>
            <Home className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">68%</div>
            <p className="text-xs text-muted-foreground">Primary residences</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Recent Transfers</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">23</div>
            <p className="text-xs text-muted-foreground">Last 30 days</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Property Owners</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">892</div>
            <p className="text-xs text-muted-foreground">Unique owners</p>
          </CardContent>
        </Card>
      </div>

      {/* Map */}
      <Card className="h-[600px]">
        <CardHeader>
          <CardTitle>Interactive Property Map</CardTitle>
          <CardDescription>Click on parcels to view detailed ownership and property information</CardDescription>
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
