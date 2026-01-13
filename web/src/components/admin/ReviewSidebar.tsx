"use client";

import { useState } from "react";
import type { STRDetailResponse, CandidateDwelling } from "@/app/admin/str-review/page";

interface ReviewSidebarProps {
  selectedListing: STRDetailResponse | null;
  onAction: (
    action: "confirm" | "reject" | "skip",
    dwellingId?: string,
    rejectionReason?: string,
    notes?: string
  ) => void;
  onJumpNext: () => void;
  hasMoreUnreviewed: boolean;
}

const REJECTION_REASONS = [
  { value: "not_str", label: "Not actually an STR" },
  { value: "duplicate", label: "Duplicate listing" },
  { value: "wrong_location", label: "Wrong location/town" },
  { value: "no_matching_dwelling", label: "No matching dwelling on parcel" },
  { value: "other", label: "Other" },
];

export default function ReviewSidebar({
  selectedListing,
  onAction,
  onJumpNext,
  hasMoreUnreviewed,
}: ReviewSidebarProps) {
  const [selectedDwellingId, setSelectedDwellingId] = useState<string | null>(null);
  const [rejectionReason, setRejectionReason] = useState<string>("");
  const [notes, setNotes] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Reset form when listing changes
  const handleConfirm = async () => {
    if (!selectedDwellingId) return;
    setIsSubmitting(true);
    await onAction("confirm", selectedDwellingId, undefined, notes || undefined);
    setSelectedDwellingId(null);
    setNotes("");
    setIsSubmitting(false);
  };

  const handleReject = async () => {
    if (!rejectionReason) return;
    setIsSubmitting(true);
    await onAction("reject", undefined, rejectionReason, notes || undefined);
    setRejectionReason("");
    setNotes("");
    setIsSubmitting(false);
  };

  const handleSkip = async () => {
    setIsSubmitting(true);
    await onAction("skip", undefined, undefined, notes || undefined);
    setNotes("");
    setIsSubmitting(false);
  };

  if (!selectedListing) {
    return (
      <div className="h-full bg-slate-800 flex items-center justify-center p-8">
        <div className="text-center">
          <div className="text-4xl mb-4">🏠</div>
          <h3 className="text-lg font-medium text-white mb-2">
            Select an STR Listing
          </h3>
          <p className="text-slate-400 text-sm">
            Click on a pin on the map to review the STR-dwelling association
          </p>
          {hasMoreUnreviewed && (
            <button
              onClick={onJumpNext}
              className="mt-4 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-medium transition-colors"
            >
              Start Reviewing →
            </button>
          )}
        </div>
      </div>
    );
  }

  const { listing, candidates } = selectedListing;

  return (
    <div className="h-full bg-slate-800 flex flex-col">
      {/* STR Listing Card */}
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-start justify-between mb-3">
          <div>
            <h2 className="text-lg font-semibold text-white leading-tight">
              {listing.name || "Unnamed Listing"}
            </h2>
            <div className="flex items-center gap-2 mt-1">
              <span
                className={`text-xs px-2 py-0.5 rounded font-medium uppercase ${
                  listing.platform === "airbnb"
                    ? "bg-red-900 text-red-200"
                    : "bg-blue-900 text-blue-200"
                }`}
              >
                {listing.platform}
              </span>
              {listing.bedrooms && (
                <span className="text-slate-400 text-sm">
                  {listing.bedrooms} BR
                </span>
              )}
            </div>
          </div>
          <span
            className={`text-xs px-2 py-1 rounded font-medium uppercase ${
              listing.review_status === "confirmed"
                ? "bg-emerald-900 text-emerald-200"
                : listing.review_status === "rejected"
                ? "bg-red-900 text-red-200"
                : listing.review_status === "skipped"
                ? "bg-yellow-900 text-yellow-200"
                : "bg-slate-700 text-slate-300"
            }`}
          >
            {listing.review_status}
          </span>
        </div>

        {/* Parcel info */}
        <div className="bg-slate-900 rounded-lg p-3">
          <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">
            Matched Parcel
          </div>
          {listing.parcel_id ? (
            <>
              <div className="text-white font-medium">
                {listing.parcel_address || "No address"}
              </div>
              <div className="text-slate-400 text-sm font-mono">
                {listing.parcel_span}
              </div>
              {listing.match_confidence && (
                <div className="text-slate-500 text-xs mt-1">
                  Spatial match: {(listing.match_confidence * 100).toFixed(0)}%
                  confidence
                </div>
              )}
            </>
          ) : (
            <div className="text-slate-500 italic">No parcel match</div>
          )}
        </div>
      </div>

      {/* Candidate Dwellings */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-slate-300 uppercase tracking-wider">
            Candidate Dwellings
          </h3>
          <span className="text-slate-500 text-sm">
            {candidates.length} found
          </span>
        </div>

        {candidates.length === 0 ? (
          <div className="bg-slate-900 rounded-lg p-4 text-center">
            <div className="text-2xl mb-2">🏚️</div>
            <p className="text-slate-400 text-sm">
              No dwellings found on this parcel
            </p>
            <p className="text-slate-500 text-xs mt-1">
              Consider rejecting with &quot;No matching dwelling&quot;
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {candidates
              .sort((a, b) => b.match_score - a.match_score)
              .map((dwelling) => (
                <DwellingCard
                  key={dwelling.id}
                  dwelling={dwelling}
                  isSelected={selectedDwellingId === dwelling.id}
                  onSelect={() => setSelectedDwellingId(dwelling.id)}
                />
              ))}
          </div>
        )}

        {/* Notes */}
        <div className="mt-4">
          <label className="block text-sm font-medium text-slate-400 mb-1">
            Notes (optional)
          </label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Add any notes about this review..."
            className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white placeholder-slate-500 text-sm focus:outline-none focus:border-emerald-500 resize-none"
            rows={2}
          />
        </div>

        {/* Rejection reason (if rejecting) */}
        <div className="mt-4">
          <label className="block text-sm font-medium text-slate-400 mb-1">
            Rejection Reason
          </label>
          <select
            value={rejectionReason}
            onChange={(e) => setRejectionReason(e.target.value)}
            className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-red-500"
          >
            <option value="">Select a reason...</option>
            {REJECTION_REASONS.map((reason) => (
              <option key={reason.value} value={reason.value}>
                {reason.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="p-4 border-t border-slate-700 bg-slate-850">
        <div className="flex gap-2 mb-3">
          <button
            onClick={handleConfirm}
            disabled={!selectedDwellingId || isSubmitting}
            className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
              selectedDwellingId && !isSubmitting
                ? "bg-emerald-600 hover:bg-emerald-500 text-white"
                : "bg-slate-700 text-slate-500 cursor-not-allowed"
            }`}
          >
            ✓ Confirm
          </button>
          <button
            onClick={handleReject}
            disabled={!rejectionReason || isSubmitting}
            className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
              rejectionReason && !isSubmitting
                ? "bg-red-600 hover:bg-red-500 text-white"
                : "bg-slate-700 text-slate-500 cursor-not-allowed"
            }`}
          >
            ✗ Reject
          </button>
          <button
            onClick={handleSkip}
            disabled={isSubmitting}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-medium transition-colors"
          >
            Skip
          </button>
        </div>

        {hasMoreUnreviewed && (
          <button
            onClick={onJumpNext}
            className="w-full px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
          >
            Jump to Next Unreviewed
            <span>→</span>
          </button>
        )}
      </div>
    </div>
  );
}

// Dwelling card component
function DwellingCard({
  dwelling,
  isSelected,
  onSelect,
}: {
  dwelling: CandidateDwelling;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const matchPercent = Math.round(dwelling.match_score * 100);

  return (
    <button
      onClick={onSelect}
      className={`w-full text-left p-3 rounded-lg border-2 transition-all ${
        isSelected
          ? "bg-emerald-900/30 border-emerald-500"
          : "bg-slate-900 border-slate-700 hover:border-slate-600"
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-white font-medium">
              {dwelling.unit_number ? `Unit ${dwelling.unit_number}` : "Dwelling"}
            </span>
            {dwelling.bedrooms && (
              <span className="text-slate-400 text-sm">
                {dwelling.bedrooms} BR
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 mt-1 text-sm">
            {dwelling.use_type && (
              <span className="text-xs px-1.5 py-0.5 rounded bg-slate-700 text-slate-300">
                {dwelling.use_type}
              </span>
            )}
            {dwelling.homestead_filed ? (
              <span className="text-xs px-1.5 py-0.5 rounded bg-emerald-900 text-emerald-200">
                Homestead
              </span>
            ) : (
              <span className="text-xs px-1.5 py-0.5 rounded bg-orange-900 text-orange-200">
                Non-Homestead
              </span>
            )}
          </div>
          {dwelling.existing_str_id && (
            <div className="text-yellow-400 text-xs mt-1 flex items-center gap-1">
              <span>⚠️</span>
              <span>Already linked to another STR</span>
            </div>
          )}
        </div>

        {/* Match score */}
        <div className="text-right">
          <div
            className={`text-lg font-bold ${
              matchPercent >= 70
                ? "text-emerald-400"
                : matchPercent >= 40
                ? "text-yellow-400"
                : "text-slate-500"
            }`}
          >
            {matchPercent}%
          </div>
          <div className="text-slate-500 text-xs">match</div>
        </div>
      </div>

      {/* Selection indicator */}
      <div className="mt-2 flex items-center gap-2">
        <div
          className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
            isSelected
              ? "border-emerald-500 bg-emerald-500"
              : "border-slate-600"
          }`}
        >
          {isSelected && (
            <svg
              className="w-2.5 h-2.5 text-white"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                clipRule="evenodd"
              />
            </svg>
          )}
        </div>
        <span
          className={`text-xs ${isSelected ? "text-emerald-400" : "text-slate-500"}`}
        >
          {isSelected ? "Selected" : "Click to select"}
        </span>
      </div>
    </button>
  );
}
