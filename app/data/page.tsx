"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Database, Download, Eye, Shield, RefreshCw, Code, MapPin, Users, Calendar, FileText } from "lucide-react"
import Link from "next/link"

const dataSources = [
  {
    name: "Vermont Property Transfer Tax Returns",
    description: "Official property sale records from Vermont Department of Taxes",
    updateFrequency: "Monthly",
    lastUpdated: "2024-01-15",
    coverage: "All property transfers in Mad River Valley",
    reliability: "High - Official state records",
  },
  {
    name: "Vermont Grand List",
    description: "Annual property assessments and ownership records",
    updateFrequency: "Annually",
    lastUpdated: "2024-04-01",
    coverage: "All assessed properties",
    reliability: "High - Municipal assessor data",
  },
  {
    name: "Town Meeting Minutes & Agendas",
    description: "Official municipal government proceedings",
    updateFrequency: "Weekly",
    lastUpdated: "2024-01-20",
    coverage: "Warren, Fayston, Waitsfield, Moretown, Duxbury",
    reliability: "High - Official municipal records",
  },
  {
    name: "Community Event Calendars",
    description: "Local organization and library event listings",
    updateFrequency: "Daily",
    lastUpdated: "2024-01-22",
    coverage: "Public events across Mad River Valley",
    reliability: "Medium - Varies by organization",
  },
]

const tableCategories = [
  {
    name: "Property Data",
    icon: MapPin,
    description: "Core property and ownership information",
    tables: [
      { name: "parcels", description: "Physical land parcels with boundaries and basic info", records: "~1,200" },
      { name: "units", description: "Individual addressable units within parcels", records: "~1,400" },
      { name: "parcel_owners", description: "Property-owning entities (individuals, LLCs, trusts)", records: "~800" },
      { name: "parcel_ownership", description: "Historical ownership transfers and sales", records: "~3,500" },
    ],
  },
  {
    name: "Community Data",
    icon: Users,
    description: "Geographic and social community groupings",
    tables: [
      { name: "communities", description: "Towns, watersheds, neighborhoods, and other groupings", records: "~15" },
      { name: "parcel_communities", description: "Links parcels to their communities", records: "~2,000" },
      { name: "community_metrics", description: "Historical metrics and trends by community", records: "~150" },
    ],
  },
  {
    name: "Events & Calendar",
    icon: Calendar,
    description: "Community events and municipal meetings",
    tables: [
      { name: "events", description: "Community events, town meetings, and workshops", records: "~200" },
      { name: "organizations", description: "Groups that organize events and create content", records: "~25" },
      { name: "event_communities", description: "Links events to affected communities", records: "~300" },
    ],
  },
  {
    name: "Member Directory",
    icon: Users,
    description: "Community member profiles and connections",
    tables: [
      { name: "members", description: "Community platform users and their profiles", records: "~45" },
      { name: "member_locations", description: "Approximate member locations for privacy", records: "~50" },
      { name: "memberships", description: "Member roles in different communities", records: "~60" },
    ],
  },
  {
    name: "Content & Documents",
    icon: FileText,
    description: "Updates, documents, and data provenance",
    tables: [
      { name: "updates", description: "Community updates and policy announcements", records: "~30" },
      { name: "documents", description: "Deeds, permits, and other official documents", records: "~500" },
      { name: "data_sources", description: "Tracks provenance of all imported data", records: "~10" },
    ],
  },
]

const apiEndpoints = [
  {
    endpoint: "/api/properties",
    method: "GET",
    description: "Search properties by location, type, or ownership",
    params: "?community=warren&type=residential&limit=50",
  },
  {
    endpoint: "/api/transfers",
    method: "GET",
    description: "Property transfer history and trends",
    params: "?since=2020-01-01&community=mad-river-valley",
  },
  {
    endpoint: "/api/events",
    method: "GET",
    description: "Upcoming community events and meetings",
    params: "?start_date=2024-01-01&community=warren",
  },
  {
    endpoint: "/api/communities/{id}/metrics",
    method: "GET",
    description: "Historical metrics for a specific community",
    params: "?metric_type=str_percentage&years=5",
  },
]

export default function DataPage() {
  const [activeTab, setActiveTab] = useState("overview")

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center space-x-3 mb-4">
            <Database className="h-8 w-8 text-primary" />
            <div>
              <h1 className="text-3xl font-bold text-foreground">Community Data</h1>
              <p className="text-muted-foreground">
                Transparent, locally-sourced information about the Mad River Valley
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary" className="flex items-center gap-1">
              <RefreshCw className="h-3 w-3" />
              Updated Daily
            </Badge>
            <Badge variant="outline" className="flex items-center gap-1">
              <Shield className="h-3 w-3" />
              Privacy Protected
            </Badge>
            <Badge variant="outline" className="flex items-center gap-1">
              <Eye className="h-3 w-3" />
              Open Access
            </Badge>
          </div>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="sources">Data Sources</TabsTrigger>
            <TabsTrigger value="schema">Database Schema</TabsTrigger>
            <TabsTrigger value="api">API Access</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Our Data Philosophy</CardTitle>
                <CardDescription>Building community through transparency and local data stewardship</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="prose prose-sm max-w-none">
                  <p>
                    Open Valley believes that communities are stronger when residents have access to clear, accurate
                    information about their neighborhoods. We collect and maintain local data to help Warren area
                    residents understand housing trends, stay informed about civic matters, and connect with their
                    neighbors.
                  </p>

                  <h4 className="font-semibold mt-6 mb-3">Our Approach</h4>
                  <ul className="space-y-2">
                    <li>
                      <strong>Local Storage:</strong> We save all data locally and update it regularly from official
                      sources
                    </li>
                    <li>
                      <strong>Source Verification:</strong> Every data point is linked to its original, authoritative
                      source
                    </li>
                    <li>
                      <strong>Privacy First:</strong> Personal information is protected and only shared with explicit
                      consent
                    </li>
                    <li>
                      <strong>Community Owned:</strong> This data belongs to the community and should be accessible to
                      all
                    </li>
                  </ul>
                </div>
              </CardContent>
            </Card>

            <div className="grid md:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <MapPin className="h-5 w-5" />
                    Property Data
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground mb-4">
                    Comprehensive property ownership and transfer records for trend analysis
                  </p>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span>Total Parcels:</span>
                      <span className="font-medium">1,247</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Property Transfers (2020-2024):</span>
                      <span className="font-medium">486</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Last Updated:</span>
                      <span className="font-medium">Jan 15, 2024</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Users className="h-5 w-5" />
                    Community Directory
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground mb-4">
                    Member-contributed profiles for neighborhood connections
                  </p>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span>Active Members:</span>
                      <span className="font-medium">45</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Communities Covered:</span>
                      <span className="font-medium">5</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Privacy Protected:</span>
                      <span className="font-medium">100%</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="sources" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Data Sources & Verification</CardTitle>
                <CardDescription>Where our information comes from and how we ensure accuracy</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {dataSources.map((source, index) => (
                    <div key={index} className="border rounded-lg p-4 space-y-3">
                      <div className="flex items-start justify-between">
                        <h4 className="font-semibold">{source.name}</h4>
                        <Badge variant={source.reliability.startsWith("High") ? "default" : "secondary"}>
                          {source.reliability.split(" - ")[0]}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">{source.description}</p>
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                        <div>
                          <span className="font-medium">Update Frequency:</span>
                          <br />
                          <span className="text-muted-foreground">{source.updateFrequency}</span>
                        </div>
                        <div>
                          <span className="font-medium">Last Updated:</span>
                          <br />
                          <span className="text-muted-foreground">{source.lastUpdated}</span>
                        </div>
                        <div>
                          <span className="font-medium">Coverage:</span>
                          <br />
                          <span className="text-muted-foreground">{source.coverage}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="schema" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Database Schema</CardTitle>
                <CardDescription>Our data model organized by functional area</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-8">
                  {tableCategories.map((category, index) => {
                    const IconComponent = category.icon
                    return (
                      <div key={index} className="space-y-4">
                        <div className="flex items-center gap-3">
                          <IconComponent className="h-6 w-6 text-primary" />
                          <div>
                            <h3 className="text-lg font-semibold">{category.name}</h3>
                            <p className="text-sm text-muted-foreground">{category.description}</p>
                          </div>
                        </div>
                        <div className="grid gap-3 ml-9">
                          {category.tables.map((table, tableIndex) => (
                            <div key={tableIndex} className="border rounded-lg p-3 bg-muted/30">
                              <div className="flex items-center justify-between mb-2">
                                <code className="text-sm font-mono bg-muted px-2 py-1 rounded">{table.name}</code>
                                <Badge variant="outline" className="text-xs">
                                  {table.records} records
                                </Badge>
                              </div>
                              <p className="text-sm text-muted-foreground">{table.description}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="api" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>API Access</CardTitle>
                <CardDescription>Programmatic access to community data for researchers and developers</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="bg-muted/50 rounded-lg p-4">
                  <h4 className="font-semibold mb-2">Getting Started</h4>
                  <p className="text-sm text-muted-foreground mb-3">
                    Our API provides read-only access to aggregated, privacy-protected community data. No authentication
                    required for public endpoints.
                  </p>
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline">
                      <Code className="h-4 w-4 mr-2" />
                      View Documentation
                    </Button>
                    <Button size="sm" variant="outline">
                      <Download className="h-4 w-4 mr-2" />
                      Download Sample Data
                    </Button>
                  </div>
                </div>

                <div className="space-y-4">
                  <h4 className="font-semibold">Available Endpoints</h4>
                  {apiEndpoints.map((endpoint, index) => (
                    <div key={index} className="border rounded-lg p-4 space-y-2">
                      <div className="flex items-center gap-3">
                        <Badge variant="outline" className="font-mono text-xs">
                          {endpoint.method}
                        </Badge>
                        <code className="text-sm font-mono">{endpoint.endpoint}</code>
                      </div>
                      <p className="text-sm text-muted-foreground">{endpoint.description}</p>
                      {endpoint.params && (
                        <div className="text-xs">
                          <span className="text-muted-foreground">Example: </span>
                          <code className="bg-muted px-1 py-0.5 rounded">{endpoint.params}</code>
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                  <h4 className="font-semibold text-amber-800 mb-2">Rate Limits & Fair Use</h4>
                  <p className="text-sm text-amber-700">
                    Please use our API responsibly. Current limits: 1000 requests per hour per IP. For higher volume
                    needs, please{" "}
                    <Link href="/contact" className="underline">
                      contact us
                    </Link>
                    .
                  </p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        <footer className="mt-16 pt-8 border-t border-border">
          <div className="grid md:grid-cols-3 gap-8">
            <div>
              <h3 className="font-semibold mb-3">About Open Valley</h3>
              <p className="text-sm text-muted-foreground mb-4">
                A community platform for the Mad River Valley, strengthening connections through transparent data and
                local engagement.
              </p>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" asChild>
                  <Link href="/">
                    <MapPin className="h-4 w-4 mr-2" />
                    Dashboard
                  </Link>
                </Button>
                <Button variant="outline" size="sm" asChild>
                  <Link href="/join">
                    <Users className="h-4 w-4 mr-2" />
                    Join Community
                  </Link>
                </Button>
              </div>
            </div>

            <div>
              <h3 className="font-semibold mb-3">Data & Privacy</h3>
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Shield className="h-4 w-4" />
                  Privacy-first approach
                </div>
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Database className="h-4 w-4" />
                  Locally stored data
                </div>
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Eye className="h-4 w-4" />
                  Open source methodology
                </div>
              </div>
            </div>

            <div>
              <h3 className="font-semibold mb-3">Contact & Support</h3>
              <p className="text-sm text-muted-foreground mb-2">
                Open Valley is maintained by <span className="font-medium">Macon Phillips</span>
              </p>
              <p className="text-sm text-muted-foreground mb-4">Questions about the data or platform? Get in touch.</p>
              <div className="flex gap-2">
                <Button variant="outline" size="sm">
                  <FileText className="h-4 w-4 mr-2" />
                  Contact
                </Button>
                <Button variant="outline" size="sm">
                  <Code className="h-4 w-4 mr-2" />
                  GitHub
                </Button>
              </div>
            </div>
          </div>

          <div className="mt-8 pt-6 border-t border-border text-center">
            <p className="text-sm text-muted-foreground">
              © 2024 Open Valley • Built for the Mad River Valley community
            </p>
          </div>
        </footer>
      </div>
    </div>
  )
}
