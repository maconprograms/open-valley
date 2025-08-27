import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { MapPin, Home } from "lucide-react"

export default function NotFound() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
      <Card className="w-full max-w-md text-center shadow-lg">
        <CardHeader className="pb-4">
          <div className="flex justify-center mb-4">
            <MapPin className="h-16 w-16 text-primary" />
          </div>
          <CardTitle className="text-2xl font-bold text-balance">Page Not Found</CardTitle>
          <CardDescription className="text-base">
            Sorry, we couldn't find the page you're looking for in the Mad River Valley community data.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            The page may have been moved, deleted, or you may have entered an incorrect URL.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Button asChild className="flex items-center gap-2">
              <Link href="/">
                <Home className="h-4 w-4" />
                Back to Dashboard
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link href="/data">View Data Sources</Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
