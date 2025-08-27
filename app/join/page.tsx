"use client"

import type React from "react"

import { useState } from "react"
import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { ArrowLeft, Shield, Users, Mail, MapPin, CheckCircle, Clock, Heart } from "lucide-react"

export default function JoinMembership() {
  const [formData, setFormData] = useState({
    firstName: "",
    lastName: "",
    email: "",
    phone: "",
    hometown: "",
    bio: "",
    interests: "",
    agreeToTerms: false,
    agreeToNewsletter: true,
  })
  const [isSubmitted, setIsSubmitted] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // Here we would normally send the data to our backend
    console.log("Membership application:", formData)
    setIsSubmitted(true)
  }

  const handleInputChange = (field: string, value: string | boolean) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  if (isSubmitted) {
    return (
      <div className="min-h-screen bg-background">
        <div className="container mx-auto px-6 py-8">
          <div className="max-w-2xl mx-auto">
            <div className="text-center mb-8">
              <Link href="/" className="inline-flex items-center text-primary hover:underline mb-4">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Dashboard
              </Link>
            </div>

            <Card className="text-center">
              <CardContent className="pt-8 pb-8">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                  <CheckCircle className="h-8 w-8 text-green-600" />
                </div>
                <h1 className="text-2xl font-bold mb-4">Application Submitted!</h1>
                <p className="text-muted-foreground mb-6">
                  Thank you for your interest in joining the Warren community directory. We'll review your application
                  and get back to you within 2-3 business days.
                </p>
                <div className="bg-muted p-4 rounded-lg mb-6">
                  <div className="flex items-center justify-center space-x-2 text-sm text-muted-foreground">
                    <Clock className="h-4 w-4" />
                    <span>Manual approval helps us maintain a safe, trusted community</span>
                  </div>
                </div>
                <Button asChild>
                  <Link href="/">Return to Dashboard</Link>
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-6 py-8">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="text-center mb-8">
            <Link href="/" className="inline-flex items-center text-primary hover:underline mb-4">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Dashboard
            </Link>
            <h1 className="text-3xl font-bold mb-2">Join the Warren Community Directory</h1>
            <p className="text-muted-foreground">
              Connect with neighbors, stay informed, and strengthen our Mad River Valley community
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Benefits Section */}
            <div className="lg:col-span-1 space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Heart className="h-5 w-5 text-primary" />
                    <span>Membership Benefits</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-start space-x-3">
                    <Users className="h-5 w-5 text-primary mt-0.5" />
                    <div>
                      <h4 className="font-medium">Community Directory</h4>
                      <p className="text-sm text-muted-foreground">
                        Connect with neighbors, find carpools, organize playdates
                      </p>
                    </div>
                  </div>
                  <div className="flex items-start space-x-3">
                    <Mail className="h-5 w-5 text-primary mt-0.5" />
                    <div>
                      <h4 className="font-medium">Email Newsletter</h4>
                      <p className="text-sm text-muted-foreground">Weekly updates on community events and local news</p>
                    </div>
                  </div>
                  <div className="flex items-start space-x-3">
                    <MapPin className="h-5 w-5 text-primary mt-0.5" />
                    <div>
                      <h4 className="font-medium">Local Insights</h4>
                      <p className="text-sm text-muted-foreground">
                        Property data, town meetings, and civic engagement
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Shield className="h-5 w-5 text-green-600" />
                    <span>Privacy & Safety</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3 text-sm text-muted-foreground">
                    <p>• Manual approval process ensures trusted community</p>
                    <p>• Your information is only visible to approved members</p>
                    <p>• You control what details to share</p>
                    <p>• No data is sold or shared with third parties</p>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Application Form */}
            <div className="lg:col-span-2">
              <Card>
                <CardHeader>
                  <CardTitle>Membership Application</CardTitle>
                  <CardDescription>Tell us a bit about yourself to join our community directory</CardDescription>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleSubmit} className="space-y-6">
                    {/* Basic Information */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <Label htmlFor="firstName">First Name *</Label>
                        <Input
                          id="firstName"
                          value={formData.firstName}
                          onChange={(e) => handleInputChange("firstName", e.target.value)}
                          required
                        />
                      </div>
                      <div>
                        <Label htmlFor="lastName">Last Name *</Label>
                        <Input
                          id="lastName"
                          value={formData.lastName}
                          onChange={(e) => handleInputChange("lastName", e.target.value)}
                          required
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <Label htmlFor="email">Email Address *</Label>
                        <Input
                          id="email"
                          type="email"
                          value={formData.email}
                          onChange={(e) => handleInputChange("email", e.target.value)}
                          required
                        />
                      </div>
                      <div>
                        <Label htmlFor="phone">Phone Number</Label>
                        <Input
                          id="phone"
                          type="tel"
                          value={formData.phone}
                          onChange={(e) => handleInputChange("phone", e.target.value)}
                          placeholder="Optional"
                        />
                      </div>
                    </div>

                    <div>
                      <Label htmlFor="hometown">Hometown/Location</Label>
                      <Input
                        id="hometown"
                        value={formData.hometown}
                        onChange={(e) => handleInputChange("hometown", e.target.value)}
                        placeholder="e.g., Warren, VT or Originally from Boston, MA"
                      />
                    </div>

                    <div>
                      <Label htmlFor="bio">Tell us about yourself</Label>
                      <Textarea
                        id="bio"
                        value={formData.bio}
                        onChange={(e) => handleInputChange("bio", e.target.value)}
                        placeholder="Share a bit about your background, family, what brings you to the Mad River Valley..."
                        rows={4}
                      />
                    </div>

                    <div>
                      <Label htmlFor="interests">Interests & Hobbies</Label>
                      <Input
                        id="interests"
                        value={formData.interests}
                        onChange={(e) => handleInputChange("interests", e.target.value)}
                        placeholder="e.g., Hiking, Skiing, Local History, Community Events"
                      />
                    </div>

                    {/* Agreement Checkboxes */}
                    <div className="space-y-4 pt-4 border-t">
                      <div className="flex items-start space-x-3">
                        <Checkbox
                          id="agreeToTerms"
                          checked={formData.agreeToTerms}
                          onCheckedChange={(checked) => handleInputChange("agreeToTerms", checked as boolean)}
                          required
                        />
                        <div className="text-sm">
                          <Label htmlFor="agreeToTerms" className="font-medium">
                            I agree to the community guidelines *
                          </Label>
                          <p className="text-muted-foreground mt-1">
                            I will use the directory respectfully for community connection and understand that my
                            information will be visible to other approved members.
                          </p>
                        </div>
                      </div>

                      <div className="flex items-start space-x-3">
                        <Checkbox
                          id="agreeToNewsletter"
                          checked={formData.agreeToNewsletter}
                          onCheckedChange={(checked) => handleInputChange("agreeToNewsletter", checked as boolean)}
                        />
                        <div className="text-sm">
                          <Label htmlFor="agreeToNewsletter" className="font-medium">
                            Subscribe to weekly community newsletter
                          </Label>
                          <p className="text-muted-foreground mt-1">
                            Get updates on local events, town meetings, and community news.
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Submit Button */}
                    <div className="pt-4">
                      <Button
                        type="submit"
                        className="w-full"
                        disabled={
                          !formData.agreeToTerms || !formData.firstName || !formData.lastName || !formData.email
                        }
                      >
                        Submit Application
                      </Button>
                      <p className="text-xs text-muted-foreground text-center mt-2">
                        We'll review your application and get back to you within 2-3 business days
                      </p>
                    </div>
                  </form>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
