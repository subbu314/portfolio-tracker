import type { Overview } from "@/lib/api";

export type WindowKey = "ITD" | "1Y" | "3Y" | "5Y";
export type MetricKey = "absolute" | "xirr" | "cagr";

export const WINDOW_KEYS: WindowKey[] = ["ITD", "1Y", "3Y", "5Y"];
export const METRIC_KEYS: MetricKey[] = ["absolute", "xirr", "cagr"];

export type WindowsMap = Overview["windows"];
export type WindowMetrics = NonNullable<WindowsMap["ITD"]>;

export function getWindowMetrics(
  windows: WindowsMap,
  key: WindowKey,
): WindowMetrics | null {
  return windows[key] ?? null;
}

export function pickReturnPct(
  metrics: WindowMetrics | null,
  metric: MetricKey,
): number | null {
  if (!metrics) return null;
  if (metric === "absolute") return metrics.absolute_pct ?? null;
  if (metric === "xirr") return metrics.xirr ?? null;
  return metrics.cagr ?? null;
}

export function pickExcessPp(
  metrics: WindowMetrics | null,
  metric: MetricKey,
): number | null {
  if (!metrics) return null;
  if (metric === "absolute") return metrics.absolute_excess_pp ?? null;
  if (metric === "xirr") return metrics.xirr_excess_pp ?? null;
  return metrics.cagr_excess_pp ?? null;
}

export function pickBenchmarkReturn(metrics: WindowMetrics | null): number | null {
  return metrics?.benchmark_return ?? null;
}

export function metricLabel(metric: MetricKey): string {
  if (metric === "absolute") return "Absolute";
  if (metric === "xirr") return "XIRR";
  return "CAGR";
}
