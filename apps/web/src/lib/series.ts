import type { HoldingSeries, PortfolioSeries } from "@/lib/api";

export type SeriesChartPoint = {
  date: string;
  portfolio: number | null;
  benchmark: number | null;
};

export function toPortfolioChartPoints(
  series: PortfolioSeries | null,
): SeriesChartPoint[] {
  return (series?.points ?? []).map((point) => ({
    date: point.date,
    portfolio: point.portfolio_return ?? null,
    benchmark: point.benchmark_return ?? null,
  }));
}

export function toHoldingChartPoints(
  series: HoldingSeries | null,
): SeriesChartPoint[] {
  return (series?.points ?? []).map((point) => ({
    date: point.date,
    portfolio: point.holding_return ?? null,
    benchmark: point.benchmark_return ?? null,
  }));
}
