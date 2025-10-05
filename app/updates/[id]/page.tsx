"use client";

import { createClient } from "@/lib/supabase/client";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Calendar, Share2 } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

interface Update {
  id: string;
  title: string;
  content: string;
  excerpt: string;
  category: string;
  published_at: string;
  created_at: string;
}

export default async function UpdateDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const supabase = createClient();

  const { data: update, error } = await supabase
    .from("updates")
    .select("*")
    .eq("id", params.id)
    .single();

  if (error || !update) {
    notFound();
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case "data-release":
        return "bg-blue-100 text-blue-800 hover:bg-blue-200";
      case "policy":
        return "bg-amber-100 text-amber-800 hover:bg-amber-200";
      case "research":
        return "bg-green-100 text-green-800 hover:bg-green-200";
      default:
        return "bg-gray-100 text-gray-800 hover:bg-gray-200";
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <Link href="/">
            <Button variant="ghost" className="mb-4">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Dashboard
            </Button>
          </Link>

          <div className="flex items-center gap-4 mb-4">
            <Badge className={getCategoryColor(update.category)}>
              {update.category.replace("-", " ").toUpperCase()}
            </Badge>
            <div className="flex items-center text-gray-600 text-sm">
              <Calendar className="w-4 h-4 mr-1" />
              {formatDate(update.published_at)}
            </div>
          </div>

          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            {update.title}
          </h1>

          <p className="text-xl text-gray-600 leading-relaxed">
            {update.excerpt}
          </p>
        </div>

        {/* Content */}
        <Card className="mb-8">
          <CardContent className="p-8">
            <div className="prose prose-lg max-w-none">
              {update.content.split("\n\n").map((paragraph, index) => (
                <p key={index} className="mb-4 text-gray-700 leading-relaxed">
                  {paragraph}
                </p>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Share Section */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">Share this update</h3>
              <Button
                variant="outline"
                onClick={() => {
                  navigator.clipboard.writeText(window.location.href);
                }}
              >
                <Share2 className="w-4 h-4 mr-2" />
                Copy Link
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600">
              Share this Warren, VT community update with others interested in
              local property data and housing trends.
            </p>
            <div className="mt-4 p-3 bg-gray-100 rounded-lg">
              <code className="text-sm text-gray-800 break-all">
                {typeof window !== "undefined"
                  ? window.location.href
                  : `https://your-domain.com/updates/${update.id}`}
              </code>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
