"use client";

interface StatCard {
  label: string;
  value: string | number;
  delta?: string;
  deltaType?: "positive" | "negative" | "neutral";
}

interface StatsData {
  cards: StatCard[];
}

interface StatsArtifactProps {
  data: unknown;
}

export default function StatsArtifact({ data }: StatsArtifactProps) {
  const statsData = data as StatsData;

  if (!statsData?.cards || statsData.cards.length === 0) {
    return (
      <div className="p-4 text-gray-400 text-center">
        No stats available
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-4">
      {statsData.cards.map((card, index) => (
        <div
          key={index}
          className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm"
        >
          <p className="text-sm font-medium text-gray-500">{card.label}</p>
          <p className="mt-1 text-2xl font-semibold text-gray-900">
            {formatValue(card.value)}
          </p>
          {card.delta && (
            <p
              className={`mt-1 text-sm ${
                card.deltaType === "positive"
                  ? "text-green-600"
                  : card.deltaType === "negative"
                  ? "text-red-600"
                  : "text-gray-500"
              }`}
            >
              {card.delta}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

function formatValue(value: string | number): string {
  if (typeof value === "number") {
    if (value >= 1000000) {
      return `$${(value / 1000000).toFixed(1)}M`;
    }
    if (value >= 1000) {
      return value.toLocaleString();
    }
    return value.toString();
  }
  return value;
}
