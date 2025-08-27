"use client"

import { useState } from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select"
import { ChevronDown, MapPin, Plus, Home, Calendar, TrendingUp, Users, Search, User, Map } from "lucide-react"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, PieChart, Pie, Cell } from "recharts"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"

// Sample data for the dashboard
const propertyTransferData = [
  { month: "Jan", transfers: 12 },
  { month: "Feb", transfers: 8 },
  { month: "Mar", transfers: 15 },
  { month: "Apr", transfers: 22 },
  { month: "May", transfers: 28 },
  { month: "Jun", transfers: 31 },
]

const propertyTypeData = [
  { type: "Single Family", count: 145, percentage: 65 },
  { type: "Condo", count: 42, percentage: 19 },
  { type: "Multi-Family", count: 28, percentage: 13 },
  { type: "Land", count: 7, percentage: 3 },
]

const residencyTypeData = [
  { type: "Primary", value: 35, color: "#0ea5e9" },
  { type: "Secondary", value: 45, color: "#f59e0b" },
  { type: "Rental", value: 20, color: "#10b981" },
]

const upcomingEvents = [
  { date: "2024-01-15", title: "Town Planning Meeting", type: "meeting" },
  { date: "2024-01-22", title: "Property Assessment Review", type: "review" },
  { date: "2024-02-01", title: "Housing Committee Meeting", type: "meeting" },
  { date: "2024-02-10", title: "Zoning Board Hearing", type: "hearing" },
]

const recentUpdates = [
  {
    id: "update-1",
    date: "2024-01-10",
    title: "New Property Transfer Data Available",
    description: "December 2023 property transfer records have been added to the database.",
    type: "data",
  },
  {
    id: "update-2",
    date: "2024-01-08",
    title: "Zoning Changes Approved",
    description: "Town approved new mixed-use zoning for the village center area.",
    type: "policy",
  },
  {
    id: "update-3",
    date: "2024-01-05",
    title: "Housing Study Released",
    description: "Mad River Valley Housing Coalition published their annual housing needs assessment.",
    type: "report",
  },
]

const communities = [
  { value: "mad-river-valley", label: "Mad River Valley" },
  { value: "warren", label: "Warren" },
  { value: "fayston", label: "Fayston" },
  { value: "waitsfield", label: "Waitsfield" },
  { value: "moretown", label: "Moretown" },
  { value: "duxbury", label: "Duxbury" },
]

export default function WarrenVTDashboard() {
  const [activeTab, setActiveTab] = useState("dashboard")
  const [selectedCommunity, setSelectedCommunity] = useState("mad-river-valley")

  const currentCommunity = communities.find((c) => c.value === selectedCommunity) || communities[0]
  const isFiltered = selectedCommunity !== "mad-river-valley"

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <MapPin className="h-8 w-8 text-primary" />
              <div>
                <Select value={selectedCommunity} onValueChange={setSelectedCommunity}>
                  <SelectTrigger className="border-none p-0 h-auto bg-transparent hover:bg-transparent focus:ring-0 focus:ring-offset-0">
                    <div className="flex items-center space-x-2">
                      <div>
                        <h1
                          className={`text-3xl font-bold tracking-tight ${isFiltered ? "text-primary" : "text-foreground"}`}
                        >
                          {currentCommunity.label}, VT
                        </h1>
                        <div className="flex items-center space-x-2 mt-1">
                          <p className="text-sm text-muted-foreground font-medium">
                            {isFiltered ? "Filtered • Community Data" : "Mad River Valley Community Data"}
                          </p>
                          {isFiltered && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-auto p-1 text-xs text-primary hover:text-primary/80 font-medium"
                              onClick={() => setSelectedCommunity("mad-river-valley")}
                            >
                              Show All
                            </Button>
                          )}
                        </div>
                      </div>
                      <ChevronDown className="h-4 w-4 text-muted-foreground" />
                    </div>
                  </SelectTrigger>
                  <SelectContent>
                    {communities.map((community) => (
                      <SelectItem key={community.value} value={community.value}>
                        {community.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <Link href="/join">
                <Button size="lg" className="font-medium">
                  <Plus className="h-4 w-4 mr-2" />
                  Join Open Valley
                </Button>
              </Link>
              <Link href="/data">
                <Button variant="outline" size="lg" className="font-medium bg-transparent">
                  Data Sources
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-6 py-8">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-6 mb-8 h-12">
            <TabsTrigger value="dashboard" className="flex items-center space-x-2 font-medium">
              <TrendingUp className="h-4 w-4" />
              <span>Dashboard</span>
            </TabsTrigger>
            <TabsTrigger value="housing" className="flex items-center space-x-2 font-medium">
              <Home className="h-4 w-4" />
              <span>Housing</span>
            </TabsTrigger>
            <TabsTrigger value="map" className="flex items-center space-x-2 font-medium">
              <Map className="h-4 w-4" />
              <span>Maps</span>
            </TabsTrigger>
            <TabsTrigger value="calendar" className="flex items-center space-x-2 font-medium">
              <Calendar className="h-4 w-4" />
              <span>Calendar</span>
            </TabsTrigger>
            <TabsTrigger value="updates" className="flex items-center space-x-2 font-medium">
              <TrendingUp className="h-4 w-4" />
              <span>Updates</span>
            </TabsTrigger>
            <TabsTrigger value="directory" className="flex items-center space-x-2 font-medium">
              <Users className="h-4 w-4" />
              <span>Directory</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard" className="space-y-8">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <h2 className="text-3xl font-bold tracking-tight">Community Overview</h2>
                <p className="text-lg text-muted-foreground">Key metrics and insights for the Mad River Valley</p>
              </div>
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-4 gap-6">
              <Card className="shadow-sm">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
                  <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                    Total Parcels
                  </CardTitle>
                  <Home className="h-5 w-5 text-muted-foreground" />
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="text-3xl font-bold tracking-tight">1,247</div>
                  <p className="text-sm text-muted-foreground mt-1 font-medium">+2.1% from last year</p>
                </CardContent>
              </Card>

              <Card className="shadow-sm">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
                  <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                    Events This Month
                  </CardTitle>
                  <Calendar className="h-5 w-5 text-muted-foreground" />
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="text-3xl font-bold tracking-tight">12</div>
                  <p className="text-sm text-muted-foreground mt-1 font-medium">+3 from last month</p>
                </CardContent>
              </Card>

              <Card className="shadow-sm">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
                  <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                    YTD Transfers
                  </CardTitle>
                  <TrendingUp className="h-5 w-5 text-muted-foreground" />
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="text-3xl font-bold tracking-tight">116</div>
                  <p className="text-sm text-muted-foreground mt-1 font-medium">+15.2% from last year</p>
                </CardContent>
              </Card>

              <Card className="shadow-sm">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
                  <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                    Secondary Homes
                  </CardTitle>
                  <Users className="h-5 w-5 text-muted-foreground" />
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="text-3xl font-bold tracking-tight">45%</div>
                  <p className="text-sm text-muted-foreground mt-1 font-medium">+3.2% from last year</p>
                </CardContent>
              </Card>
            </div>

            {/* Charts */}
            <div className="grid grid-cols-2 gap-6">
              <Card className="shadow-sm">
                <CardHeader className="pb-4">
                  <CardTitle className="text-xl font-semibold">Property Transfers by Month</CardTitle>
                  <CardDescription className="text-base">2024 transfer activity</CardDescription>
                </CardHeader>
                <CardContent>
                  <ChartContainer
                    config={{
                      transfers: {
                        label: "Property Transfers",
                        color: "#0ea5e9",
                      },
                    }}
                    className="h-[300px]"
                  >
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={propertyTransferData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="month" />
                        <YAxis />
                        <ChartTooltip content={<ChartTooltipContent labelKey="month" nameKey="transfers" />} />
                        <Bar dataKey="transfers" fill="#0ea5e9" />
                      </BarChart>
                    </ResponsiveContainer>
                  </ChartContainer>
                </CardContent>
              </Card>

              <Card className="shadow-sm">
                <CardHeader className="pb-4">
                  <CardTitle className="text-xl font-semibold">Property Use Distribution</CardTitle>
                  <CardDescription className="text-base">Current residency patterns</CardDescription>
                </CardHeader>
                <CardContent>
                  <ChartContainer
                    config={{
                      primary: { label: "Primary", color: "#0ea5e9" },
                      secondary: { label: "Secondary", color: "#f59e0b" },
                      rental: { label: "Rental", color: "#10b981" },
                    }}
                    className="h-[300px]"
                  >
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={residencyTypeData}
                          cx="50%"
                          cy="50%"
                          outerRadius={80}
                          fill="#8884d8"
                          dataKey="value"
                          label={({ type, value }) => `${type}: ${value}%`}
                        >
                          {residencyTypeData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <ChartTooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  </ChartContainer>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="housing" className="space-y-8">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <h2 className="text-3xl font-bold tracking-tight">Housing Data</h2>
                <p className="text-lg text-muted-foreground">Property information and market trends</p>
              </div>
            </div>

            {/* Housing-specific metrics */}
            <div className="grid grid-cols-3 gap-6">
              <Card className="shadow-sm">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
                  <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                    Median Home Value
                  </CardTitle>
                  <Home className="h-5 w-5 text-muted-foreground" />
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="text-3xl font-bold tracking-tight">$525,000</div>
                  <p className="text-sm text-muted-foreground mt-1 font-medium">+8.2% from last year</p>
                </CardContent>
              </Card>

              <Card className="shadow-sm">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
                  <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                    Homestead Properties
                  </CardTitle>
                  <Home className="h-5 w-5 text-muted-foreground" />
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="text-3xl font-bold tracking-tight">55%</div>
                  <p className="text-sm text-muted-foreground mt-1 font-medium">-2.1% from last year</p>
                </CardContent>
              </Card>

              <Card className="shadow-sm">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
                  <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                    Days on Market
                  </CardTitle>
                  <TrendingUp className="h-5 w-5 text-muted-foreground" />
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="text-3xl font-bold tracking-tight">42</div>
                  <p className="text-sm text-muted-foreground mt-1 font-medium">-15 days from last year</p>
                </CardContent>
              </Card>
            </div>

            {/* Property Type Breakdown */}
            <Card className="shadow-sm">
              <CardHeader className="pb-4">
                <CardTitle className="text-xl font-semibold">Property Types</CardTitle>
                <CardDescription className="text-base">Distribution of property classifications</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-4 gap-4">
                  {propertyTypeData.map((type, index) => (
                    <div key={index} className="text-center p-4 bg-muted/50 rounded-lg">
                      <div className="text-2xl font-bold text-primary">{type.count}</div>
                      <div className="text-sm font-medium text-muted-foreground">{type.type}</div>
                      <div className="text-xs text-muted-foreground">{type.percentage}%</div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="map" className="space-y-8">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <h2 className="text-3xl font-bold tracking-tight">Maps</h2>
                <p className="text-lg text-muted-foreground">Interactive maps and data visualizations</p>
              </div>
            </div>

            {/* Maps Grid */}
            <div className="grid grid-cols-2 gap-6">
              <Link href="/maps/property-overview">
                <Card className="h-[300px] cursor-pointer hover:shadow-lg transition-all duration-200 shadow-sm group">
                  <CardContent className="p-6 flex flex-col justify-between h-full">
                    <div className="space-y-4">
                      <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                        <Home className="h-6 w-6 text-primary" />
                      </div>
                      <div>
                        <h3 className="text-xl font-semibold mb-2">Property Overview</h3>
                        <p className="text-muted-foreground text-base leading-relaxed">
                          Interactive map showing all parcels, ownership data, and property classifications across the
                          Mad River Valley.
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center justify-between pt-4">
                      <Badge variant="secondary" className="font-medium">
                        1,247 parcels
                      </Badge>
                      <span className="text-sm text-primary font-medium group-hover:underline">View Map →</span>
                    </div>
                  </CardContent>
                </Card>
              </Link>

              <Link href="/maps/transfer-activity">
                <Card className="h-[300px] cursor-pointer hover:shadow-lg transition-all duration-200 shadow-sm group">
                  <CardContent className="p-6 flex flex-col justify-between h-full">
                    <div className="space-y-4">
                      <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                        <TrendingUp className="h-6 w-6 text-primary" />
                      </div>
                      <div>
                        <h3 className="text-xl font-semibold mb-2">Transfer Activity</h3>
                        <p className="text-muted-foreground text-base leading-relaxed">
                          Visualize recent property transfers, sales trends, and market activity patterns over time.
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center justify-between pt-4">
                      <Badge variant="secondary" className="font-medium">
                        116 YTD transfers
                      </Badge>
                      <span className="text-sm text-primary font-medium group-hover:underline">View Map →</span>
                    </div>
                  </CardContent>
                </Card>
              </Link>

              <Link href="/maps/zoning-districts">
                <Card className="h-[300px] cursor-pointer hover:shadow-lg transition-all duration-200 shadow-sm group">
                  <CardContent className="p-6 flex flex-col justify-between h-full">
                    <div className="space-y-4">
                      <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                        <Map className="h-6 w-6 text-primary" />
                      </div>
                      <div>
                        <h3 className="text-xl font-semibold mb-2">Zoning Districts</h3>
                        <p className="text-muted-foreground text-base leading-relaxed">
                          Explore zoning classifications, permitted uses, and regulatory boundaries across communities.
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center justify-between pt-4">
                      <Badge variant="secondary" className="font-medium">
                        5 communities
                      </Badge>
                      <span className="text-sm text-primary font-medium group-hover:underline">View Map →</span>
                    </div>
                  </CardContent>
                </Card>
              </Link>

              <Link href="/maps/community-assets">
                <Card className="h-[300px] cursor-pointer hover:shadow-lg transition-all duration-200 shadow-sm group">
                  <CardContent className="p-6 flex flex-col justify-between h-full">
                    <div className="space-y-4">
                      <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                        <Users className="h-6 w-6 text-primary" />
                      </div>
                      <div>
                        <h3 className="text-xl font-semibold mb-2">Community Assets</h3>
                        <p className="text-muted-foreground text-base leading-relaxed">
                          Locate schools, parks, trails, and other community resources throughout the valley.
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center justify-between pt-4">
                      <Badge variant="secondary" className="font-medium">
                        Coming soon
                      </Badge>
                      <span className="text-sm text-muted-foreground font-medium">View Map →</span>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            </div>
          </TabsContent>

          <TabsContent value="calendar" className="space-y-8">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <h2 className="text-3xl font-bold tracking-tight">Community Calendar</h2>
                <p className="text-lg text-muted-foreground">Upcoming meetings and events</p>
              </div>
            </div>

            {/* Events List - Now full width */}
            <div className="space-y-6">
              <div>
                <div className="space-y-4">
                  <h3 className="text-xl font-semibold mb-6">Upcoming Events</h3>
                  {upcomingEvents.map((event, index) => (
                    <Card key={index} className="hover:shadow-md transition-all duration-200 w-full shadow-sm">
                      <CardContent className="p-6">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-6">
                            <div className="flex flex-col items-center bg-primary/10 rounded-lg p-4 min-w-[70px]">
                              <span className="text-xs font-semibold text-primary uppercase tracking-wide">
                                {new Date(event.date).toLocaleDateString("en-US", { month: "short" })}
                              </span>
                              <span className="text-2xl font-bold text-primary">{new Date(event.date).getDate()}</span>
                            </div>
                            <div className="space-y-2">
                              <h4 className="font-semibold text-lg">{event.title}</h4>
                              <Badge variant="outline" className="text-sm font-medium">
                                {event.type}
                              </Badge>
                            </div>
                          </div>
                          <Button variant="outline" size="lg" className="font-medium bg-transparent">
                            View Details
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="updates" className="space-y-8">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <h2 className="text-3xl font-bold tracking-tight">Community Updates</h2>
                <p className="text-lg text-muted-foreground">Latest news and policy changes</p>
              </div>
              <Button size="lg" className="font-medium">
                Subscribe to Updates
              </Button>
            </div>

            <div className="grid gap-6">
              {recentUpdates.map((update) => (
                <Card key={update.id} className="shadow-sm hover:shadow-md transition-all duration-200">
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between">
                      <div className="space-y-3">
                        <div className="flex items-center space-x-3">
                          <Badge variant="outline" className="font-medium">
                            {update.type}
                          </Badge>
                          <span className="text-sm text-muted-foreground font-medium">{update.date}</span>
                        </div>
                        <Link href={`/updates/${update.id}`}>
                          <h3 className="text-xl font-semibold hover:text-primary cursor-pointer transition-colors">
                            {update.title}
                          </h3>
                        </Link>
                        <p className="text-muted-foreground text-base leading-relaxed">{update.description}</p>
                      </div>
                      <Link href={`/updates/${update.id}`}>
                        <Button variant="outline" size="lg" className="font-medium bg-transparent">
                          Read More
                        </Button>
                      </Link>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="directory" className="space-y-8">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <h2 className="text-3xl font-bold tracking-tight">Community Directory</h2>
                <p className="text-lg text-muted-foreground">Connect with your Warren neighbors</p>
              </div>
              <div className="flex items-center space-x-4">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
                  <input
                    type="text"
                    placeholder="Search members..."
                    className="pl-10 pr-4 py-3 border border-input rounded-md bg-background text-base font-medium w-64"
                  />
                </div>
                <Link href="/join">
                  <Button size="lg" className="font-medium">
                    <Plus className="h-4 w-4 mr-2" />
                    Join Open Valley
                  </Button>
                </Link>
              </div>
            </div>

            <div className="grid grid-cols-4 gap-6">
              <Link href="/directory/sarah-johnson">
                <Card className="h-[300px] cursor-pointer hover:shadow-lg transition-all duration-200 shadow-sm">
                  <CardContent className="p-6 flex flex-col justify-between h-full">
                    <div className="flex flex-col items-center text-center space-y-4">
                      <img
                        src="/friendly-woman-with-hiking-gear.png"
                        alt="Sarah Johnson"
                        className="w-16 h-16 rounded-full object-cover"
                      />
                      <div>
                        <h3 className="font-semibold text-lg">Sarah Johnson</h3>
                        <p className="text-sm text-muted-foreground font-medium">Warren, VT</p>
                      </div>
                    </div>
                    <div className="space-y-3">
                      <Badge className="bg-green-100 text-green-800 border-green-200 font-medium">
                        Full-time Resident
                      </Badge>
                      <div className="flex flex-wrap gap-1">
                        <Badge variant="secondary" className="text-xs font-medium">
                          Hiking
                        </Badge>
                        <Badge variant="secondary" className="text-xs font-medium">
                          Volunteering
                        </Badge>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </Link>

              <Link href="/directory/tom-miller">
                <Card className="h-[300px] cursor-pointer hover:shadow-lg transition-all duration-200 shadow-sm">
                  <CardContent className="p-6 flex flex-col justify-between h-full">
                    <div className="flex flex-col items-center text-center space-y-4">
                      <img
                        src="/man-with-beard-and-flannel-shirt.png"
                        alt="Tom Miller"
                        className="w-16 h-16 rounded-full object-cover"
                      />
                      <div>
                        <h3 className="font-semibold text-lg">Tom Miller</h3>
                        <p className="text-sm text-muted-foreground font-medium">Originally Boston, MA</p>
                      </div>
                    </div>
                    <div className="space-y-3">
                      <div className="h-6"></div>
                      <div className="flex flex-wrap gap-1">
                        <Badge variant="secondary" className="text-xs font-medium">
                          Tech
                        </Badge>
                        <Badge variant="secondary" className="text-xs font-medium">
                          Sustainability
                        </Badge>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </Link>

              <Link href="/directory/jenny-adams">
                <Card className="h-[300px] cursor-pointer hover:shadow-lg transition-all duration-200 shadow-sm">
                  <CardContent className="p-6 flex flex-col justify-between h-full">
                    <div className="flex flex-col items-center text-center space-y-4">
                      <img
                        src="/smiling-older-woman.png"
                        alt="Jenny Adams"
                        className="w-16 h-16 rounded-full object-cover"
                      />
                      <div>
                        <h3 className="font-semibold text-lg">Jenny Adams</h3>
                        <p className="text-sm text-muted-foreground font-medium">Warren, VT (born and raised)</p>
                      </div>
                    </div>
                    <div className="space-y-3">
                      <Badge className="bg-green-100 text-green-800 border-green-200 font-medium">
                        Full-time Resident
                      </Badge>
                      <div className="flex flex-wrap gap-1">
                        <Badge variant="secondary" className="text-xs font-medium">
                          Local History
                        </Badge>
                        <Badge variant="secondary" className="text-xs font-medium">
                          Community Events
                        </Badge>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </Link>

              <Link href="/directory/mike-chen">
                <Card className="h-[300px] cursor-pointer hover:shadow-lg transition-all duration-200 shadow-sm">
                  <CardContent className="p-6 flex flex-col justify-between h-full">
                    <div className="flex flex-col items-center text-center space-y-4">
                      <User className="w-16 h-16 rounded-full bg-muted p-4 text-muted-foreground" />
                      <div>
                        <h3 className="font-semibold text-lg">Mike Chen</h3>
                        <p className="text-sm text-muted-foreground font-medium">Waitsfield, VT</p>
                      </div>
                    </div>
                    <div className="space-y-3">
                      <div className="h-6"></div>
                      <div className="flex flex-wrap gap-1">
                        <Badge variant="secondary" className="text-xs font-medium">
                          Photography
                        </Badge>
                        <Badge variant="secondary" className="text-xs font-medium">
                          Skiing
                        </Badge>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            </div>

            <div className="mt-8 p-6 bg-muted/50 rounded-lg border">
              <h3 className="font-semibold text-lg mb-2">Members Only</h3>
              <p className="text-base text-muted-foreground">
                This directory is only visible to authenticated community members
              </p>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
