"use client";

import { useState } from "react";
import Link from "next/link";

interface StatCardProps {
  value: string | number;
  label: string;
  tooltip?: {
    title: string;
    description: string;
    details?: { label: string; value: string }[];
    link?: { href: string; label: string };
  };
  color?: "green" | "orange" | "blue" | "slate" | "red" | "purple" | "emerald" | "amber" | "brown";
  size?: "default" | "large";
}

const colorClasses = {
  green: {
    bg: "bg-green-50",
    border: "border-green-200",
    accent: "bg-green-500",
    text: "text-green-700",
    tooltipBg: "bg-green-900",
  },
  emerald: {
    bg: "bg-emerald-50",
    border: "border-emerald-300",
    accent: "bg-emerald-500",
    text: "text-emerald-700",
    tooltipBg: "bg-emerald-900",
  },
  orange: {
    bg: "bg-orange-50",
    border: "border-orange-200",
    accent: "bg-orange-500",
    text: "text-orange-700",
    tooltipBg: "bg-orange-900",
  },
  amber: {
    bg: "bg-amber-50",
    border: "border-amber-300",
    accent: "bg-amber-500",
    text: "text-amber-700",
    tooltipBg: "bg-amber-900",
  },
  blue: {
    bg: "bg-blue-50",
    border: "border-blue-200",
    accent: "bg-blue-500",
    text: "text-blue-700",
    tooltipBg: "bg-blue-900",
  },
  slate: {
    bg: "bg-slate-50",
    border: "border-slate-200",
    accent: "bg-slate-500",
    text: "text-slate-700",
    tooltipBg: "bg-slate-900",
  },
  red: {
    bg: "bg-red-50",
    border: "border-red-200",
    accent: "bg-red-500",
    text: "text-red-700",
    tooltipBg: "bg-red-900",
  },
  purple: {
    bg: "bg-purple-50",
    border: "border-purple-200",
    accent: "bg-purple-500",
    text: "text-purple-700",
    tooltipBg: "bg-purple-900",
  },
  brown: {
    bg: "bg-amber-100",
    border: "border-amber-400",
    accent: "bg-amber-700",
    text: "text-amber-800",
    tooltipBg: "bg-amber-900",
  },
};

export default function StatCard({
  value,
  label,
  tooltip,
  color = "slate",
  size = "default",
}: StatCardProps) {
  const colors = colorClasses[color];
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div
      className="relative"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div
        className={`
          ${colors.bg} ${colors.border}
          rounded-xl border p-6
          transition-all duration-200
          hover:shadow-md hover:scale-[1.02]
          cursor-default
        `}
      >
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <p className="text-sm font-medium text-slate-500 uppercase tracking-wide">
              {label}
            </p>
            <p
              className={`
                mt-2 font-bold text-slate-900
                ${size === "large" ? "text-4xl" : "text-3xl"}
              `}
            >
              {typeof value === "number" ? value.toLocaleString() : value}
            </p>
          </div>
          <div className={`${colors.accent} w-1 h-12 rounded-full`} />
        </div>
      </div>

      {/* Hover tooltip */}
      {tooltip && isHovered && (
        <div
          className={`
            absolute z-20 left-0 right-0 top-full mt-2
            ${colors.tooltipBg} text-white
            rounded-lg shadow-xl p-4
            animate-in fade-in slide-in-from-top-2 duration-200
          `}
        >
          <p className="font-semibold text-sm">{tooltip.title}</p>
          <p className="text-sm text-white/80 mt-1">{tooltip.description}</p>
          {tooltip.details && tooltip.details.length > 0 && (
            <div className="mt-3 pt-3 border-t border-white/20 space-y-1">
              {tooltip.details.map((detail, i) => (
                <div key={i} className="flex justify-between text-sm">
                  <span className="text-white/70">{detail.label}</span>
                  <span className="font-medium">{detail.value}</span>
                </div>
              ))}
            </div>
          )}
          {tooltip.link && (
            <div className="mt-3 pt-3 border-t border-white/20">
              <Link
                href={tooltip.link.href}
                className="text-sm text-white/90 hover:text-white underline underline-offset-2"
              >
                {tooltip.link.label} &rarr;
              </Link>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
