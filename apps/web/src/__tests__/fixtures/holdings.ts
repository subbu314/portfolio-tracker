import type { Holding } from "@/lib/api";
import type { WindowMetrics } from "@/lib/windows";

export function makeWindows(
  overrides: Partial<WindowMetrics> = {},
): Holding["windows"] {
  const itd: WindowMetrics = {
    absolute_pct: 0.2,
    absolute_inr: 40,
    xirr: 0.15,
    cagr: null,
    benchmark_return: 0.1,
    absolute_excess_pp: 10,
    xirr_excess_pp: 5,
    cagr_excess_pp: null,
    ...overrides,
  };
  return {
    ITD: itd,
    "1Y": null,
    "3Y": null,
    "5Y": null,
  };
}

export function makeHolding(overrides: Partial<Holding> = {}): Holding {
  return {
    instrument_id: 1,
    symbol: "RELIANCE",
    instrument_type: "equity",
    qty: 2,
    avg_price: 100,
    ltp: 120,
    value: 240,
    absolute_pct: 0.2,
    absolute_inr: 40,
    xirr: 0.15,
    cagr: null,
    benchmark: "Nifty 500",
    benchmark_return: 0.1,
    absolute_excess_pp: 10,
    xirr_excess_pp: 5,
    cagr_excess_pp: null,
    incomplete: false,
    needs_category: false,
    mf_category: null,
    windows: makeWindows(),
    ...overrides,
  };
}
