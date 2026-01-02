"use client";

interface StatCardProps {
  value: string | number;
  label: string;
  subtext?: string;
  color?: "green" | "orange" | "blue" | "slate" | "red";
  size?: "default" | "large";
}

const colorClasses = {
  green: {
    bg: "bg-green-50",
    border: "border-green-200",
    accent: "bg-green-500",
    text: "text-green-700",
  },
  orange: {
    bg: "bg-orange-50",
    border: "border-orange-200",
    accent: "bg-orange-500",
    text: "text-orange-700",
  },
  blue: {
    bg: "bg-blue-50",
    border: "border-blue-200",
    accent: "bg-blue-500",
    text: "text-blue-700",
  },
  slate: {
    bg: "bg-slate-50",
    border: "border-slate-200",
    accent: "bg-slate-500",
    text: "text-slate-700",
  },
  red: {
    bg: "bg-red-50",
    border: "border-red-200",
    accent: "bg-red-500",
    text: "text-red-700",
  },
};

export default function StatCard({
  value,
  label,
  subtext,
  color = "slate",
  size = "default",
}: StatCardProps) {
  const colors = colorClasses[color];

  return (
    <div
      className={`
        ${colors.bg} ${colors.border}
        rounded-xl border p-6
        transition-all duration-200
        hover:shadow-md hover:scale-[1.02]
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
          {subtext && (
            <p className={`mt-1 text-sm ${colors.text}`}>{subtext}</p>
          )}
        </div>
        <div className={`${colors.accent} w-1 h-12 rounded-full`} />
      </div>
    </div>
  );
}
