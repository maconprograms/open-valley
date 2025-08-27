import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ArrowLeft, Mail, Phone, MapPin, Heart, PawPrint, Shield, User } from "lucide-react"
import Link from "next/link"

// This would be fetched from Supabase based on the ID
const memberProfile = {
  id: "sample_user_1",
  firstName: "Sarah",
  lastName: "Johnson",
  displayName: "Sarah J.",
  bio: "Long-time Warren resident, love hiking the local trails and volunteering at the school. Always happy to help newcomers get settled! I've been here for over 15 years and know all the best spots for everything from quiet walks to family adventures.",
  hometown: "Warren, VT",
  isFullTimeResident: true,
  partnerName: "Mike Johnson",
  children: ["Emma (12)", "Jake (9)"],
  pets: ["Buddy (Golden Retriever)", "Whiskers (Cat)"],
  phone: "(802) 555-0123",
  email: "sarah.johnson@email.com",
  socialLinks: {
    instagram: "@sarahj_warren",
    facebook: "sarah.johnson.warren",
  },
  profileImageUrl: "/friendly-woman-with-hiking-gear.png",
  interests: ["Hiking", "Volunteering", "Local Schools", "Community Events"],
  joinedDate: "2023-03-15",
  memberSince: "March 2023",
}

export default function MemberProfile() {
  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-6 py-6">
        <div className="mb-6">
          <Link href="/?tab=directory">
            <Button variant="ghost" className="mb-4">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Directory
            </Button>
          </Link>
        </div>

        <Card className="mb-6 border-cyan-200 bg-cyan-50/50">
          <CardContent className="pt-4">
            <div className="flex items-start space-x-3">
              <Shield className="h-5 w-5 text-cyan-600 mt-0.5 flex-shrink-0" />
              <div>
                <h3 className="font-medium text-cyan-900 mb-1">Member Directory Privacy</h3>
                <p className="text-sm text-cyan-800 leading-relaxed">
                  This information is private and only visible to approved Warren community members. All directory
                  members have been verified and agreed to use this information respectfully for community connection
                  and mutual support.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Profile Card */}
          <div className="lg:col-span-1">
            <Card>
              <CardContent className="pt-6">
                <div className="text-center">
                  {memberProfile.profileImageUrl ? (
                    <img
                      src={memberProfile.profileImageUrl || "/placeholder.svg"}
                      alt={`${memberProfile.firstName} ${memberProfile.lastName}`}
                      className="w-32 h-32 rounded-full object-cover mx-auto mb-4 border-4 border-gray-100"
                    />
                  ) : (
                    <div className="w-32 h-32 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-4 border-4 border-gray-200">
                      <User className="h-16 w-16 text-gray-400" />
                    </div>
                  )}

                  <div className="mb-4">
                    <h1 className="text-2xl font-bold">
                      {memberProfile.firstName} {memberProfile.lastName}
                    </h1>
                    <div className="flex items-center justify-center gap-2 mt-2">
                      {memberProfile.isFullTimeResident && (
                        <Badge className="bg-green-100 text-green-800 border-green-200">Full-time Resident</Badge>
                      )}
                    </div>
                  </div>

                  <div className="space-y-3 text-left">
                    <div className="flex items-center space-x-2">
                      <MapPin className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm">{memberProfile.hometown}</span>
                    </div>

                    <div className="flex items-center space-x-2">
                      <Mail className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm">{memberProfile.email}</span>
                    </div>

                    <div className="flex items-center space-x-2">
                      <Phone className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm">{memberProfile.phone}</span>
                    </div>

                    <div className="flex items-center space-x-2">
                      <User className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm">Member since {memberProfile.memberSince}</span>
                    </div>
                  </div>

                  <div className="mt-6 space-y-2">
                    <Button className="w-full bg-cyan-600 hover:bg-cyan-700">
                      <Mail className="h-4 w-4 mr-2" />
                      Send Message
                    </Button>
                    <Button variant="outline" className="w-full bg-transparent">
                      <Phone className="h-4 w-4 mr-2" />
                      Call
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Details */}
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>About</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground leading-relaxed mb-6">{memberProfile.bio}</p>

                <div>
                  <h4 className="font-medium mb-3">Interests</h4>
                  <div className="flex flex-wrap gap-2">
                    {memberProfile.interests.map((interest, index) => (
                      <Badge key={index} variant="secondary" className="bg-amber-100 text-amber-800 border-amber-200">
                        {interest}
                      </Badge>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Heart className="h-5 w-5 text-red-500" />
                    Family
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {memberProfile.partnerName && (
                      <div>
                        <p className="text-sm font-medium text-gray-700">Partner</p>
                        <p className="text-muted-foreground">{memberProfile.partnerName}</p>
                      </div>
                    )}

                    {memberProfile.children.length > 0 && (
                      <div>
                        <p className="text-sm font-medium text-gray-700">Children</p>
                        <div className="space-y-1">
                          {memberProfile.children.map((child, index) => (
                            <p key={index} className="text-muted-foreground text-sm">
                              {child}
                            </p>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <PawPrint className="h-5 w-5 text-amber-600" />
                    Pets
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-1">
                    {memberProfile.pets.map((pet, index) => (
                      <p key={index} className="text-muted-foreground text-sm">
                        {pet}
                      </p>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Connect</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-3">
                  {memberProfile.socialLinks.instagram && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="bg-gradient-to-r from-purple-500 to-pink-500 text-white border-0 hover:from-purple-600 hover:to-pink-600"
                    >
                      Instagram
                    </Button>
                  )}
                  {memberProfile.socialLinks.facebook && (
                    <Button variant="outline" size="sm" className="bg-blue-600 text-white border-0 hover:bg-blue-700">
                      Facebook
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}
