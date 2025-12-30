"use client";

import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface ChartData {
  title?: string;
  data: Array<{
    label: string;
    value: number;
    color?: string;
  }>;
  xLabel?: string;
  yLabel?: string;
}

interface ChartArtifactProps {
  type: "pie_chart" | "bar_chart";
  data: unknown;
}

const COLORS = [
  "#22c55e", // green
  "#f97316", // orange
  "#3b82f6", // blue
  "#a855f7", // purple
  "#ec4899", // pink
  "#14b8a6", // teal
  "#f59e0b", // amber
  "#ef4444", // red
];

export default function ChartArtifact({ type, data }: ChartArtifactProps) {
  const chartData = data as ChartData;

  if (!chartData?.data || chartData.data.length === 0) {
    return (
      <div className="h-80 flex items-center justify-center text-gray-400">
        No chart data available
      </div>
    );
  }

  // Transform data for Recharts
  const formattedData = chartData.data.map((item, index) => ({
    name: item.label,
    value: item.value,
    fill: item.color || COLORS[index % COLORS.length],
  }));

  if (type === "pie_chart") {
    return (
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={formattedData}
              cx="50%"
              cy="50%"
              labelLine={true}
              label={({ name, percent }) =>
                `${name}: ${(percent * 100).toFixed(0)}%`
              }
              outerRadius={100}
              dataKey="value"
            >
              {formattedData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number) => [
                value.toLocaleString(),
                "Count",
              ]}
            />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>
    );
  }

  // Bar chart
  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={formattedData}
          margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 12 }}
            angle={-45}
            textAnchor="end"
            height={60}
            label={
              chartData.xLabel
                ? { value: chartData.xLabel, position: "bottom", offset: 0 }
                : undefined
            }
          />
          <YAxis
            tick={{ fontSize: 12 }}
            tickFormatter={(value) =>
              value >= 1000000
                ? `$${(value / 1000000).toFixed(1)}M`
                : value >= 1000
                ? `$${(value / 1000).toFixed(0)}K`
                : value.toString()
            }
            label={
              chartData.yLabel
                ? {
                    value: chartData.yLabel,
                    angle: -90,
                    position: "insideLeft",
                  }
                : undefined
            }
          />
          <Tooltip
            formatter={(value: number) => [
              `$${value.toLocaleString()}`,
              "Value",
            ]}
          />
          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
            {formattedData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
