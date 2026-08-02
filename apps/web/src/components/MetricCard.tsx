"use client";

import { useState } from "react";
import { MetricWindowSelects } from "@/components/MetricWindowSelects";
import { formatPct, formatPp } from "@/lib/format";
import {
  getWindowMetrics,
  pickBenchmarkReturn,
  pickExcessPp,
  pickReturnPct,
  type MetricKey,
  type WindowKey,
  type WindowsMap,
} from "@/lib/windows";

type Props = {
  title: string;
  windows: WindowsMap;
  mode: "return" | "outperformance";
  defaultMetric: MetricKey;
};

export function MetricCard({
  title,
  windows,
  mode,
  defaultMetric,
}: Props) {
  const [metric, setMetric] = useState<MetricKey>(defaultMetric);
  const [window, setWindow] = useState<WindowKey>("ITD");
  const metrics = getWindowMetrics(windows, window);
  const portfolioReturn = pickReturnPct(metrics, metric);
  const benchmarkReturn = pickBenchmarkReturn(metrics);
  const value =
    mode === "return"
      ? formatPct(portfolioReturn)
      : formatPp(pickExcessPp(metrics, metric));

  return (
    <section className="metric-card">
      <div className="panel-head">
        <h2>{title}</h2>
        <MetricWindowSelects
          metric={metric}
          window={window}
          onMetricChange={setMetric}
          onWindowChange={setWindow}
        />
      </div>
      <p className="metric-value">{value}</p>
      {mode === "outperformance" ? (
        <>
          <p className="muted">You beat category benchmarks by {value}</p>
          {portfolioReturn !== null && benchmarkReturn !== null ? (
            <p className="metric-breakdown">
              {formatPct(portfolioReturn)} − {formatPct(benchmarkReturn)}
            </p>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
