import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { WarrenMapbox } from "@/components/warren-mapbox"
import { MapProvider } from "@/components/mapbox/map-provider"
import { TrendingUp, DollarSign, Calendar, Activity } from "lucide-react"

export default function TransferActivityMap() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold text-balance">Transfer Activity Map</h1>
        <p className="text-lg text-muted-foreground text-pretty">
          Visualize recent property transfers, sales trends, and market activity patterns over time.
        </p>
      </div>

      {/* Transfer Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">YTD Transfers</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">116</div>
            <p className="text-xs text-muted-foreground">+15.2% from last year</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Median Sale Price</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">$525K</div>
            <p className="text-xs text-muted-foreground">+8.3% from last year</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Recent Activity</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">23</div>
            <p className="text-xs text-muted-foreground">Last 30 days</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Market Trend</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">↗ Active</div>
            <p className="text-xs text-muted-foreground">Strong buyer interest</p>
          </CardContent>
        </Card>
      </div>

      {/* Map */}
      <Card className="h-[600px]">
        <CardHeader>
          <CardTitle>Property Transfer Activity</CardTitle>
          <CardDescription>Recent transfers are highlighted with sale dates and prices</CardDescription>
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
