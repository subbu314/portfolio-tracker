"use client";

import { useState } from "react";
import { MetricWindowSelects } from "@/components/MetricWindowSelects";
import { Card } from "@/components/ui/card";
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
  const excessPp = pickExcessPp(metrics, metric);
  const value =
    mode === "return"
      ? formatPct(portfolioReturn)
      : formatPp(excessPp);
  const outperformanceCopy =
    excessPp === null
      ? null
      : excessPp < 0
        ? `You trail category benchmarks by ${formatPp(Math.abs(excessPp)).replace("+", "")}`
        : `You beat category benchmarks by ${value}`;

  return (
    <Card className="metric-card p-5">
      <div className="panel-head">
        <h2>{title}</h2>
        <MetricWindowSelects
          idPrefix={mode === "return" ? "return" : "outperf"}
          labelPrefix={title}
          metric={metric}
          window={window}
          onMetricChange={setMetric}
          onWindowChange={setWindow}
        />
      </div>
      <p className="metric-value font-mono tabular-nums">{value}</p>
      {mode === "outperformance" ? (
        <>
          {outperformanceCopy ? <p className="muted">{outperformanceCopy}</p> : null}
          {portfolioReturn !== null && benchmarkReturn !== null ? (
            <p className="metric-breakdown font-mono tabular-nums">
              {formatPct(portfolioReturn)} − {formatPct(benchmarkReturn)}
            </p>
          ) : null}
        </>
      ) : null}
    </Card>
  );
}
