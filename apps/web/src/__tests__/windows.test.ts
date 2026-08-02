import { describe, expect, it } from "vitest";
import {
  getWindowMetrics,
  pickBenchmarkReturn,
  pickExcessPp,
  pickReturnPct,
} from "@/lib/windows";

const windows = {
  ITD: {
    absolute_pct: 0.2,
    absolute_inr: 100,
    xirr: 0.15,
    cagr: 0.12,
    benchmark_return: 0.1,
    absolute_excess_pp: 5,
    xirr_excess_pp: 2.5,
    cagr_excess_pp: 1.1,
  },
  "1Y": null,
  "3Y": null,
  "5Y": null,
} as const;

describe("windows helpers", () => {
  it("reads named window including 1Y alias key", () => {
    expect(getWindowMetrics(windows, "ITD")?.xirr).toBe(0.15);
    expect(getWindowMetrics(windows, "1Y")).toBeNull();
  });

  it("picks return and excess pp by metric", () => {
    const m = getWindowMetrics(windows, "ITD");
    expect(pickReturnPct(m, "xirr")).toBe(0.15);
    expect(pickReturnPct(m, "absolute")).toBe(0.2);
    expect(pickReturnPct(m, "cagr")).toBe(0.12);
    expect(pickExcessPp(m, "xirr")).toBe(2.5);
    expect(pickBenchmarkReturn(m)).toBe(0.1);
  });

  it("returns null when window missing", () => {
    expect(pickReturnPct(null, "xirr")).toBeNull();
    expect(pickExcessPp(null, "absolute")).toBeNull();
  });
});
