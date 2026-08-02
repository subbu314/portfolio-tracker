import { describe, expect, it } from "vitest";
import { allocationByKind } from "@/lib/allocation";
import type { Holding } from "@/lib/api";

function h(partial: Partial<Holding> & Pick<Holding, "instrument_type" | "value">): Holding {
  return {
    instrument_id: 1,
    symbol: "X",
    qty: 1,
    avg_price: 1,
    ltp: 1,
    absolute_pct: null,
    absolute_inr: null,
    xirr: null,
    cagr: null,
    benchmark: "Nifty 500",
    benchmark_return: null,
    absolute_excess_pp: null,
    xirr_excess_pp: null,
    cagr_excess_pp: null,
    incomplete: false,
    needs_category: false,
    mf_category: null,
    windows: { ITD: null, "1Y": null, "3Y": null, "5Y": null },
    ...partial,
  };
}

describe("allocationByKind", () => {
  it("aggregates equity / mf / etf weights", () => {
    const slices = allocationByKind([
      h({ instrument_type: "equity", value: 50 }),
      h({ instrument_type: "mf", value: 30 }),
      h({ instrument_type: "etf", value: 20 }),
    ]);
    expect(slices).toEqual([
      { label: "Equity", weight: 0.5 },
      { label: "Mutual funds", weight: 0.3 },
      { label: "ETFs", weight: 0.2 },
    ]);
  });

  it("omits zero buckets and handles empty", () => {
    expect(allocationByKind([h({ instrument_type: "equity", value: 10 })])).toEqual([
      { label: "Equity", weight: 1 },
    ]);
    expect(allocationByKind([])).toEqual([]);
  });
});
