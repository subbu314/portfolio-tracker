"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Props = {
  title: string;
  available: boolean;
  metricSupportsSeries: boolean;
  points: {
    date: string;
    portfolio: number | null;
    benchmark: number | null;
  }[];
  portfolioLabel?: string;
  benchmarkLabel?: string;
};

export function ReturnSeriesChart({
  title,
  available,
  metricSupportsSeries,
  points,
  portfolioLabel = "Portfolio",
  benchmarkLabel = "Benchmark",
}: Props) {
  if (!metricSupportsSeries) {
    return (
      <p className="muted">
        N/A — series chart supports Absolute return only for v1.
      </p>
    );
  }
  if (!available) {
    return <p className="muted">N/A — not enough history for this window.</p>;
  }

  const chartPoints = points.map((point) => ({
    ...point,
    portfolio: point.portfolio === null ? null : point.portfolio * 100,
    benchmark: point.benchmark === null ? null : point.benchmark * 100,
  }));

  return (
    <figure className="chart-frame" aria-label={title}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartPoints}>
          <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
          <XAxis dataKey="date" stroke="var(--muted)" />
          <YAxis
            stroke="var(--muted)"
            tickFormatter={(value: number) => `${value.toFixed(0)}%`}
          />
          <Tooltip formatter={(value) => `${Number(value).toFixed(2)}%`} />
          <Legend />
          <Line
            type="monotone"
            dataKey="portfolio"
            name={portfolioLabel}
            stroke="var(--accent)"
            dot={false}
            connectNulls={false}
          />
          <Line
            type="monotone"
            dataKey="benchmark"
            name={benchmarkLabel}
            stroke="var(--positive)"
            dot={false}
            connectNulls={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </figure>
  );
}
