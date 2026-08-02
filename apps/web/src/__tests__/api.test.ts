import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/lib/api";

const BASE = "http://127.0.0.1:8000";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function mockOk(json: unknown = {}) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => json,
    text: async () => "",
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function expectGetRequest(fetchMock: ReturnType<typeof mockOk>, path: string) {
  expect(fetchMock).toHaveBeenCalledWith(
    `${BASE}${path}`,
    expect.objectContaining({ cache: "no-store" }),
  );
  const init = fetchMock.mock.calls[0][1] as RequestInit;
  expect(init.method ?? "GET").toBe("GET");
}

describe("api client request mapping", () => {
  it("getHealth GETs /health", async () => {
    const fetchMock = mockOk({ status: "ok" });
    await api.getHealth();
    expectGetRequest(fetchMock, "/health");
  });

  it("getOverview GETs /portfolio/overview", async () => {
    const fetchMock = mockOk({
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
    });
    const result = await api.getOverview();
    expectGetRequest(fetchMock, "/portfolio/overview");
    expect(result.total_value).toBe(100);
  });

  it("getHoldings unwraps holdings array", async () => {
    const fetchMock = mockOk({ holdings: [{ symbol: "A" }] });
    const rows = await api.getHoldings();
    expectGetRequest(fetchMock, "/portfolio/holdings");
    expect(rows).toEqual([{ symbol: "A" }]);
  });

  it.each([
    ["getPerformance", () => api.getPerformance(), "/portfolio/performance"],
    ["getAlerts", () => api.getAlerts(), "/portfolio/alerts"],
    ["getAuthStatus", () => api.getAuthStatus(), "/auth/status"],
    ["getLoginUrl", () => api.getLoginUrl(), "/auth/login-url"],
    ["getBenchmarkSettings", () => api.getBenchmarkSettings(), "/settings/benchmarks"],
  ] as const)("%s GETs %s", async (_name, call, path) => {
    const fetchMock = mockOk({});
    await call();
    expectGetRequest(fetchMock, path);
  });

  it("postCallback POSTs JSON request_token", async () => {
    const fetchMock = mockOk({ connected: true });
    await api.postCallback("tok-1");
    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE}/auth/callback`,
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request_token: "tok-1" }),
        cache: "no-store",
      }),
    );
  });

  it("postLogout POSTs /auth/logout", async () => {
    const fetchMock = mockOk({ connected: false });
    await api.postLogout();
    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE}/auth/logout`,
      expect.objectContaining({ method: "POST", cache: "no-store" }),
    );
  });

  it("postSync POSTs /sync", async () => {
    const fetchMock = mockOk({});
    await api.postSync();
    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE}/sync`,
      expect.objectContaining({ method: "POST", cache: "no-store" }),
    );
  });

  it("postImportCsv sends multipart file field", async () => {
    const fetchMock = mockOk({
      format: "console_tradebook",
      new: 1,
      existing: 0,
      segment_counts: {},
      flagged_rows: [],
      date_min: null,
      date_max: null,
      financial_years: [],
    });
    const file = new File(["symbol,trade_date\n"], "eq.csv", { type: "text/csv" });
    await api.postImportCsv(file);
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(fetchMock.mock.calls[0][0]).toBe(`${BASE}/import/csv`);
    expect(init.method).toBe("POST");
    expect(init.body).toBeInstanceOf(FormData);
    expect((init.body as FormData).get("file")).toBeTruthy();
  });

  it("postImportCsvBatch appends files field", async () => {
    const fetchMock = mockOk({});
    const f1 = new File(["a"], "a.csv", { type: "text/csv" });
    const f2 = new File(["b"], "b.csv", { type: "text/csv" });
    await api.postImportCsvBatch([f1, f2]);
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(fetchMock.mock.calls[0][0]).toBe(`${BASE}/import/csv`);
    expect(init.method).toBe("POST");
    const body = init.body as FormData;
    expect(body.getAll("files")).toHaveLength(2);
  });

  it("putBenchmark PUTs JSON benchmark_index", async () => {
    const fetchMock = mockOk({});
    await api.putBenchmark(9, "NIFTY 50");
    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE}/settings/benchmarks/9`,
      expect.objectContaining({
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ benchmark_index: "NIFTY 50" }),
        cache: "no-store",
      }),
    );
  });

  it("putCategory PUTs JSON category", async () => {
    const fetchMock = mockOk({});
    await api.putCategory(9, "Large Cap");
    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE}/settings/categories/9`,
      expect.objectContaining({
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category: "Large Cap" }),
        cache: "no-store",
      }),
    );
  });

  it("getHolding GETs /portfolio/holdings/:id", async () => {
    const fetchMock = mockOk({ instrument_id: 7, symbol: "RELIANCE" });
    await api.getHolding(7);
    expectGetRequest(fetchMock, "/portfolio/holdings/7");
  });

  it("getHoldingTransactions GETs transactions path", async () => {
    const fetchMock = mockOk({ instrument_id: 7, transactions: [] });
    await api.getHoldingTransactions(7);
    expectGetRequest(fetchMock, "/portfolio/holdings/7/transactions");
  });

  it("getPortfolioSeries GETs /portfolio/series with window", async () => {
    const fetchMock = mockOk({
      window: "1Y",
      metric: "absolute",
      as_of: "2026-08-01",
      start: "2025-08-01",
      available: true,
      incomplete: false,
      points: [],
    });
    await api.getPortfolioSeries("1Y");
    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE}/portfolio/series?window=1Y`,
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("getHoldingSeries GETs holding series with window", async () => {
    const fetchMock = mockOk({
      instrument_id: 7,
      window: "ITD",
      metric: "absolute",
      benchmark: "Nifty 500",
      as_of: "2026-08-01",
      start: "2024-01-01",
      available: true,
      incomplete: false,
      points: [],
    });
    await api.getHoldingSeries(7, "ITD");
    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE}/portfolio/holdings/7/series?window=ITD`,
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("getCatalogs GETs /settings/catalogs", async () => {
    const fetchMock = mockOk({ mf_categories: [], benchmark_indexes: [] });
    await api.getCatalogs();
    expectGetRequest(fetchMock, "/settings/catalogs");
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

  it("parses FastAPI JSON detail into Error message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        statusText: "Unauthorized",
        text: async () => JSON.stringify({ detail: "Not authenticated" }),
      }),
    );
    await expect(api.getHealth()).rejects.toMatchObject({
      message: "Not authenticated",
    });
  });

  it("strips trailing slash from API base URL", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://127.0.0.1:8000/");
    vi.resetModules();
    const { api: reloaded } = await import("@/lib/api");
    const fetchMock = mockOk({ status: "ok" });

    await reloaded.getHealth();

    expect(fetchMock.mock.calls[0][0]).toBe(`${BASE}/health`);
  });
});
