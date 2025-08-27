import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { WarrenMapbox } from "@/components/warren-mapbox"
import { MapProvider } from "@/components/mapbox/map-provider"
import { School, MapPin, TreePine, Utensils } from "lucide-react"

export default function CommunityAssetsMap() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold text-balance">Community Assets Map</h1>
        <p className="text-lg text-muted-foreground text-pretty">
          Locate schools, parks, trails, and other community resources throughout the valley.
        </p>
      </div>

      {/* Asset Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Schools</CardTitle>
            <School className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">8</div>
            <p className="text-xs text-muted-foreground">Public & private</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Parks & Recreation</CardTitle>
            <TreePine className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">15</div>
            <p className="text-xs text-muted-foreground">Parks and trails</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Local Businesses</CardTitle>
            <Utensils className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">42</div>
            <p className="text-xs text-muted-foreground">Restaurants & shops</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Public Services</CardTitle>
            <MapPin className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">12</div>
            <p className="text-xs text-muted-foreground">Government & services</p>
          </CardContent>
        </Card>
      </div>

      {/* Map */}
      <Card className="h-[600px]">
        <CardHeader>
          <CardTitle>Community Resources Map</CardTitle>
          <CardDescription>Interactive map of schools, parks, businesses, and public services</CardDescription>
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
