"use client";

import { useState, useEffect, useCallback } from "react";
import STRReviewMap from "@/components/admin/STRReviewMap";
import ReviewSidebar from "@/components/admin/ReviewSidebar";

export interface STRQueueItem {
  id: string;
  platform: string;
  name: string | null;
  lat: number;
  lng: number;
  bedrooms: number | null;
  parcel_id: string | null;
  parcel_span: string | null;
  parcel_address: string | null;
  match_confidence: number | null;
  review_status: "unreviewed" | "confirmed" | "rejected" | "skipped";
  candidate_dwelling_count: number;
}

export interface CandidateDwelling {
  id: string;
  unit_number: string | null;
  use_type: string | null;
  bedrooms: number | null;
  tax_classification: string | null;
  homestead_filed: boolean;
  existing_str_id: string | null;
  existing_str_name: string | null;
  match_score: number;
}

export interface STRDetailResponse {
  listing: STRQueueItem;
  candidates: CandidateDwelling[];
  parcel_geojson: GeoJSON.Feature | null;
}

export interface ReviewStats {
  total_listings: number;
  matched_to_parcel: number;
  unreviewed: number;
  confirmed: number;
  rejected: number;
  skipped: number;
  completion_percent: number;
}

export default function STRReviewPage() {
  const [queue, setQueue] = useState<STRQueueItem[]>([]);
  const [selectedListing, setSelectedListing] = useState<STRDetailResponse | null>(null);
  const [stats, setStats] = useState<ReviewStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("unreviewed");

  const getAuthHeaders = () => {
    const token = localStorage.getItem("admin_token");
    return {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };
  };

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch(`${apiUrl}/api/admin/str-review/stats`, {
        headers: getAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (err) {
      console.error("Failed to fetch stats:", err);
    }
  }, [apiUrl]);

  const fetchQueue = useCallback(async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams({ limit: "500" });
      if (statusFilter !== "all") {
        params.set("status", statusFilter);
      }
      const response = await fetch(
        `${apiUrl}/api/admin/str-review/queue?${params}`,
        { headers: getAuthHeaders() }
      );
      if (response.ok) {
        const data = await response.json();
        setQueue(data.items);
      } else {
        setError("Failed to fetch review queue");
      }
    } catch (err) {
      console.error("Failed to fetch queue:", err);
      setError("Failed to connect to API");
    }
    setIsLoading(false);
  }, [apiUrl, statusFilter]);

  const fetchListingDetail = async (listingId: string) => {
    try {
      const response = await fetch(
        `${apiUrl}/api/admin/str-review/${listingId}`,
        { headers: getAuthHeaders() }
      );
      if (response.ok) {
        const data = await response.json();
        setSelectedListing(data);
      }
    } catch (err) {
      console.error("Failed to fetch listing detail:", err);
    }
  };

  const handleSelectListing = (listing: STRQueueItem) => {
    fetchListingDetail(listing.id);
  };

  const handleAction = async (
    action: "confirm" | "reject" | "skip",
    dwellingId?: string,
    rejectionReason?: string,
    notes?: string
  ) => {
    if (!selectedListing) return;

    try {
      const response = await fetch(
        `${apiUrl}/api/admin/str-review/${selectedListing.listing.id}/link`,
        {
          method: "PUT",
          headers: getAuthHeaders(),
          body: JSON.stringify({
            action,
            dwelling_id: dwellingId || null,
            rejection_reason: rejectionReason || null,
            notes: notes || null,
          }),
        }
      );

      if (response.ok) {
        // Refresh the queue and stats
        await fetchQueue();
        await fetchStats();

        // Jump to next unreviewed
        jumpToNext();
      }
    } catch (err) {
      console.error("Failed to submit action:", err);
    }
  };

  const jumpToNext = () => {
    // Find the next unreviewed listing
    const nextUnreviewed = queue.find(
      (item) =>
        item.review_status === "unreviewed" &&
        item.id !== selectedListing?.listing.id
    );

    if (nextUnreviewed) {
      fetchListingDetail(nextUnreviewed.id);
    } else {
      setSelectedListing(null);
    }
  };

  useEffect(() => {
    fetchQueue();
    fetchStats();
  }, [fetchQueue, fetchStats]);

  if (error) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-56px)]">
        <div className="text-center">
          <span className="text-red-400 text-lg">{error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-56px)] flex flex-col">
      {/* Header bar with stats and filters */}
      <div className="bg-slate-800 border-b border-slate-700 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <h1 className="text-lg font-semibold text-white">STR-Dwelling Review</h1>

          {/* Status filter */}
          <div className="flex items-center gap-2">
            <span className="text-slate-400 text-sm">Filter:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-700 border border-slate-600 text-white text-sm rounded px-2 py-1 focus:outline-none focus:border-emerald-500"
            >
              <option value="unreviewed">Unreviewed</option>
              <option value="confirmed">Confirmed</option>
              <option value="rejected">Rejected</option>
              <option value="skipped">Skipped</option>
              <option value="all">All</option>
            </select>
          </div>
        </div>

        {/* Progress stats */}
        {stats && (
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-4 text-sm">
              <span className="text-slate-400">
                <span className="text-emerald-400 font-medium">{stats.confirmed}</span> confirmed
              </span>
              <span className="text-slate-400">
                <span className="text-red-400 font-medium">{stats.rejected}</span> rejected
              </span>
              <span className="text-slate-400">
                <span className="text-yellow-400 font-medium">{stats.skipped}</span> skipped
              </span>
              <span className="text-slate-400">
                <span className="text-slate-300 font-medium">{stats.unreviewed}</span> remaining
              </span>
            </div>

            {/* Progress bar */}
            <div className="w-32 h-2 bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-emerald-500 transition-all duration-300"
                style={{ width: `${stats.completion_percent}%` }}
              />
            </div>
            <span className="text-emerald-400 font-medium text-sm">
              {stats.completion_percent.toFixed(1)}%
            </span>
          </div>
        )}
      </div>

      {/* Main content: Map + Sidebar */}
      <div className="flex-1 flex">
        {/* Map (60%) */}
        <div className="w-3/5 h-full">
          {isLoading ? (
            <div className="h-full flex items-center justify-center bg-slate-900">
              <div className="text-center">
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-emerald-400 mx-auto mb-3"></div>
                <span className="text-slate-300">Loading STR listings...</span>
              </div>
            </div>
          ) : (
            <STRReviewMap
              listings={queue}
              selectedListing={selectedListing}
              onSelectListing={handleSelectListing}
            />
          )}
        </div>

        {/* Sidebar (40%) */}
        <div className="w-2/5 h-full border-l border-slate-700 overflow-y-auto">
          <ReviewSidebar
            selectedListing={selectedListing}
            onAction={handleAction}
            onJumpNext={jumpToNext}
            hasMoreUnreviewed={queue.some(
              (item) =>
                item.review_status === "unreviewed" &&
                item.id !== selectedListing?.listing.id
            )}
          />
        </div>
      </div>
    </div>
  );
}
