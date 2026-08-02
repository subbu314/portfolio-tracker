import { describe, expect, it } from "vitest";
import {
  toHoldingChartPoints,
  toPortfolioChartPoints,
} from "@/lib/series";
import type { HoldingSeries, PortfolioSeries } from "@/lib/api";

describe("series mappers", () => {
  it("maps portfolio_return to portfolio", () => {
    expect(
      toPortfolioChartPoints({
        available: true,
        window: "ITD",
        metric: "absolute",
        points: [
          {
            date: "2024-01-01",
            portfolio_return: 0.1,
            benchmark_return: 0.05,
          },
        ],
      } as PortfolioSeries),
    ).toEqual([
      { date: "2024-01-01", portfolio: 0.1, benchmark: 0.05 },
    ]);
  });

  it("maps holding_return to portfolio and null series to empty", () => {
    expect(toHoldingChartPoints(null)).toEqual([]);
    expect(
      toHoldingChartPoints({
        available: true,
        window: "ITD",
        metric: "absolute",
        instrument_id: 1,
        benchmark: "Nifty 500",
        points: [
          {
            date: "2024-01-01",
            holding_return: 0.2,
            benchmark_return: null,
          },
        ],
      } as HoldingSeries),
    ).toEqual([
      { date: "2024-01-01", portfolio: 0.2, benchmark: null },
    ]);
  });
});
