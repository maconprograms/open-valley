"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from "recharts"
import { Search, Home, TrendingUp, Users, DollarSign, MapPin, Calendar, Filter, Bell, Plus } from "lucide-react"
import WarrenMapbox from "@/components/warren-mapbox"

// Sample data for the dashboard
const propertyTransferData = [
  { month: "Jan", transfers: 12, avgPrice: 485000 },
  { month: "Feb", transfers: 8, avgPrice: 520000 },
  { month: "Mar", transfers: 15, avgPrice: 475000 },
  { month: "Apr", transfers: 22, avgPrice: 510000 },
  { month: "May", transfers: 28, avgPrice: 535000 },
  { month: "Jun", transfers: 31, avgPrice: 580000 },
]

const propertyTypeData = [
  { type: "Single Family", count: 145, percentage: 65 },
  { type: "Condo", count: 42, percentage: 19 },
  { type: "Multi-Family", count: 28, percentage: 13 },
  { type: "Land", count: 7, percentage: 3 },
]

const residencyTypeData = [
  { type: "Primary", value: 35, color: "var(--chart-1)" },
  { type: "Secondary", value: 45, color: "var(--chart-2)" },
  { type: "Rental", value: 20, color: "var(--chart-3)" },
]

const upcomingEvents = [
  { date: "2024-01-15", title: "Town Planning Meeting", type: "meeting" },
  { date: "2024-01-22", title: "Property Assessment Review", type: "review" },
  { date: "2024-02-01", title: "Housing Committee Meeting", type: "meeting" },
  { date: "2024-02-10", title: "Zoning Board Hearing", type: "hearing" },
]

const recentUpdates = [
  {
    date: "2024-01-10",
    title: "New Property Transfer Data Available",
    description: "December 2023 property transfer records have been added to the database.",
    type: "data",
  },
  {
    date: "2024-01-08",
    title: "Zoning Changes Approved",
    description: "Town approved new mixed-use zoning for the village center area.",
    type: "policy",
  },
  {
    date: "2024-01-05",
    title: "Housing Study Released",
    description: "Mad River Valley Housing Coalition published their annual housing needs assessment.",
    type: "report",
  },
]

export default function WarrenVTDashboard() {
  const [activeTab, setActiveTab] = useState("dashboard")

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <MapPin className="h-8 w-8 text-primary" />
                <div>
                  <h1 className="text-2xl font-bold text-foreground">Warren, VT</h1>
                  <p className="text-sm text-muted-foreground">Mad River Valley Community Data</p>
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input placeholder="Search properties, owners..." className="pl-10 w-64" />
              </div>
              <Button variant="outline" size="sm">
                <Filter className="h-4 w-4 mr-2" />
                Filters
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-6 py-6">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3 mb-6">
            <TabsTrigger value="dashboard" className="flex items-center gap-2">
              <MapPin className="h-4 w-4" />
              Dashboard
            </TabsTrigger>
            <TabsTrigger value="calendar" className="flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              Calendar
            </TabsTrigger>
            <TabsTrigger value="updates" className="flex items-center gap-2">
              <Bell className="h-4 w-4" />
              Updates
            </TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard" className="space-y-6">
            <div className="grid grid-cols-3 gap-6 h-[500px]">
              {/* Left Column - Two Cards */}
              <div className="col-span-1 space-y-4">
                <Card className="h-[240px]">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg">Warren Overview</CardTitle>
                    <CardDescription>Mad River Valley Community</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-muted-foreground">Total Properties</span>
                        <span className="font-semibold">1,247</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-muted-foreground">Avg Value</span>
                        <span className="font-semibold">$525,000</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-muted-foreground">Secondary Homes</span>
                        <span className="font-semibold">45%</span>
                      </div>
                      <div className="pt-2">
                        <Badge variant="secondary" className="w-full justify-center">
                          <TrendingUp className="h-3 w-3 mr-1" />
                          +8.3% Value Growth
                        </Badge>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="h-[240px]">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg">Quick Actions</CardTitle>
                    <CardDescription>Explore the data</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <Button className="w-full" variant="default">
                      <Search className="h-4 w-4 mr-2" />
                      Search Properties
                    </Button>
                    <Button className="w-full bg-transparent" variant="outline">
                      <Filter className="h-4 w-4 mr-2" />
                      Filter by Type
                    </Button>
                    <Button className="w-full bg-transparent" variant="outline">
                      <TrendingUp className="h-4 w-4 mr-2" />
                      View Trends
                    </Button>
                  </CardContent>
                </Card>
              </div>

              {/* Right Side - Hero Map taking 2/3 */}
              <div className="col-span-2">
                <Card className="h-full">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg">Warren, VT Property Map</CardTitle>
                    <CardDescription>Interactive map of the Mad River Valley</CardDescription>
                  </CardHeader>
                  <CardContent className="h-[420px] p-0">
                    <WarrenMapbox />
                  </CardContent>
                </Card>
              </div>
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Properties</CardTitle>
                  <Home className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">1,247</div>
                  <p className="text-xs text-muted-foreground">+2.1% from last year</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Avg Property Value</CardTitle>
                  <DollarSign className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">$525,000</div>
                  <p className="text-xs text-muted-foreground">+8.3% from last year</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">YTD Transfers</CardTitle>
                  <TrendingUp className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">116</div>
                  <p className="text-xs text-muted-foreground">+15.2% from last year</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Secondary Homes</CardTitle>
                  <Users className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">45%</div>
                  <p className="text-xs text-muted-foreground">+3.2% from last year</p>
                </CardContent>
              </Card>
            </div>

            {/* Property Transfers Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Property Transfers by Month</CardTitle>
                <CardDescription>Number of property transfers and trends over time</CardDescription>
              </CardHeader>
              <CardContent>
                <ChartContainer
                  config={{
                    transfers: { label: "Transfers", color: "var(--chart-1)" },
                  }}
                  className="h-[300px]"
                >
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={propertyTransferData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="month" />
                      <YAxis />
                      <ChartTooltip content={<ChartTooltipContent />} />
                      <Bar dataKey="transfers" fill="var(--chart-1)" />
                    </BarChart>
                  </ResponsiveContainer>
                </ChartContainer>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="calendar" className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold">Community Calendar</h2>
                <p className="text-muted-foreground">Upcoming meetings, hearings, and important dates</p>
              </div>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Add Event
              </Button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Upcoming Events</CardTitle>
                  <CardDescription>Next 30 days</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {upcomingEvents.map((event, index) => (
                      <div key={index} className="flex items-center space-x-4 p-3 border rounded-lg">
                        <div className="flex-shrink-0">
                          <Calendar className="h-5 w-5 text-primary" />
                        </div>
                        <div className="flex-1">
                          <h4 className="font-medium">{event.title}</h4>
                          <p className="text-sm text-muted-foreground">{event.date}</p>
                        </div>
                        <Badge variant="outline">{event.type}</Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Calendar View</CardTitle>
                  <CardDescription>Interactive calendar coming soon</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-[400px] bg-muted rounded-lg flex items-center justify-center">
                    <div className="text-center">
                      <Calendar className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                      <p className="text-muted-foreground">Full calendar view will be implemented here</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="updates" className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold">Community Updates</h2>
                <p className="text-muted-foreground">Latest news, data updates, and policy changes</p>
              </div>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Add Update
              </Button>
            </div>

            <div className="space-y-4">
              {recentUpdates.map((update, index) => (
                <Card key={index}>
                  <CardContent className="pt-6">
                    <div className="flex items-start space-x-4">
                      <div className="flex-shrink-0">
                        <div className="w-2 h-2 bg-primary rounded-full mt-2"></div>
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-2">
                          <h3 className="font-semibold">{update.title}</h3>
                          <div className="flex items-center space-x-2">
                            <Badge variant="outline">{update.type}</Badge>
                            <span className="text-sm text-muted-foreground">{update.date}</span>
                          </div>
                        </div>
                        <p className="text-muted-foreground">{update.description}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
