import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/lib/api";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("api client", () => {
  it("getOverview GETs /portfolio/overview and returns JSON", async () => {
    const payload = {
      as_of: "2026-08-01",
      total_value: 100,
      absolute: {
        gain_inr: 10,
        gain_pct: 0.1,
        invested_cost: 90,
        current_value: 100,
      },
      xirr: null,
      cagr: null,
      benchmark_return: null,
      absolute_excess_pp: null,
      xirr_excess_pp: null,
      cagr_excess_pp: null,
      allocation: [],
      incomplete: false,
      windows: { ITD: null, "1Y": null, "3Y": null, "5Y": null },
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => payload,
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await api.getOverview();

    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/portfolio/overview",
      expect.objectContaining({ cache: "no-store" }),
    );
    expect(result.total_value).toBe(100);
  });

  it("postImportCsv sends multipart file field", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        format: "console_tradebook",
        new: 1,
        existing: 0,
        segment_counts: {},
        flagged_rows: [],
        date_min: null,
        date_max: null,
        financial_years: [],
      }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const file = new File(["symbol,trade_date\n"], "eq.csv", { type: "text/csv" });

    await api.postImportCsv(file);

    expect(fetchMock).toHaveBeenCalled();
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(init.body).toBeInstanceOf(FormData);
    expect((init.body as FormData).get("file")).toBeTruthy();
  });

  it("throws with response text on non-OK", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        statusText: "Bad Request",
        text: async () => "nope",
      }),
    );
    await expect(api.getHealth()).rejects.toThrow(/nope/);
  });
});
