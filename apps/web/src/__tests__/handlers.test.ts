import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, expect, it, vi } from "vitest";
import { handlers } from "@/mocks/handlers";
import { loadFixture } from "@/mocks/load-fixture";
import { STORAGE_KEY } from "@/mocks/scenarios";

const server = setupServer(...handlers);
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

beforeAll(() => server.listen());
afterEach(() => {
  server.resetHandlers();
  localStorage.clear();
});
afterAll(() => server.close());

it("serves happy overview and holdings via MSW", async () => {
  localStorage.setItem(STORAGE_KEY, "happy");
  const overview = await fetch(`${API}/portfolio/overview`).then((response) =>
    response.json(),
  );
  const holdings = await fetch(`${API}/portfolio/holdings`).then((response) =>
    response.json(),
  );

  expect(overview.total_value).toBeGreaterThan(0);
  expect(holdings.holdings.length).toBeGreaterThanOrEqual(3);
  expect(overview.absolute.gain_pct).not.toBeNull();
});

it("returns fixed sync success JSON", async () => {
  const sync = await fetch(`${API}/sync`, { method: "POST" }).then((response) =>
    response.json(),
  );

  expect(sync).toHaveProperty("holdings_count");
  expect(sync).toHaveProperty("last_sync_at");
});

it("returns 404 for unknown holding id", async () => {
  localStorage.setItem(STORAGE_KEY, "happy");
  const response = await fetch(`${API}/portfolio/holdings/999`);

  expect(response.status).toBe(404);
  expect(await response.json()).toEqual({ detail: "Holding not found" });
});

it("sync returns 401 when logged_out", async () => {
  localStorage.setItem(STORAGE_KEY, "logged_out");
  const response = await fetch(`${API}/sync`, { method: "POST" });

  expect(response.status).toBe(401);
});

it("import returns 400 for import_errors scenario", async () => {
  localStorage.setItem(STORAGE_KEY, "import_errors");
  const response = await fetch(`${API}/import/csv`, {
    method: "POST",
    body: new FormData(),
  });

  expect(response.status).toBe(400);
});

it.each([
  ["empty", async () => {
    localStorage.setItem(STORAGE_KEY, "empty");
    const [h, o, s] = await Promise.all([
      fetch(`${API}/portfolio/holdings`).then((r) => r.json()),
      fetch(`${API}/portfolio/overview`).then((r) => r.json()),
      fetch(`${API}/portfolio/series?window=ITD`).then((r) => r.json()),
    ]);
    expect(h.holdings).toEqual([]);
    expect(o.total_value).toBe(0);
    expect(o.absolute.current_value).toBe(0);
    expect(o.absolute.invested_cost).toBe(0);
    expect(o.absolute.gain_inr).toBe(0);
    expect(o.absolute.gain_pct).toBeNull();
    expect(o.xirr).toBeNull();
    expect(o.cagr).toBeNull();
    expect(o.windows.ITD).toBeNull();
    expect(o.windows["1Y"]).toBeNull();
    expect(o.allocation).toEqual([]);
    expect(s.available).toBe(false);
  }],
  ["logged_out", async () => {
    localStorage.setItem(STORAGE_KEY, "logged_out");
    const a = await fetch(`${API}/auth/status`).then((r) => r.json());
    expect(a.connected).toBe(false);
    expect(a.last_sync_at).toBeNull();
    expect(a.last_trade_append_at).toBeNull();
  }],
  ["stale", async () => {
    localStorage.setItem(STORAGE_KEY, "stale");
    const a = await fetch(`${API}/auth/status`).then((r) => r.json());
    expect(a.last_sync_at).toMatch(/^2020-/);
  }],
  ["gap", async () => {
    localStorage.setItem(STORAGE_KEY, "gap");
    const a = await fetch(`${API}/portfolio/alerts`).then((r) => r.json());
    expect(a.gap?.suggested_from).toBeTruthy();
    expect(a.gap?.message).toBeTruthy();
    expect(a.gap?.suggested_to).toBeTruthy();
  }],
  ["unknown_category", async () => {
    localStorage.setItem(STORAGE_KEY, "unknown_category");
    const [b, h, detail] = await Promise.all([
      fetch(`${API}/settings/benchmarks`).then((r) => r.json()),
      fetch(`${API}/portfolio/holdings`).then((r) => r.json()),
      fetch(`${API}/portfolio/holdings/3`).then((r) => r.json()),
    ]);
    expect(
      b.items.some((i: { needs_category: boolean }) => i.needs_category),
    ).toBe(true);
    expect(
      b.items.every(
        (i: { needs_category: boolean; mf_category: string | null }) =>
          !i.needs_category || i.mf_category === null,
      ),
    ).toBe(true);
    expect(
      h.holdings.some(
        (x: { needs_category: boolean }) => x.needs_category === true,
      ),
    ).toBe(true);
    expect(
      h.holdings.every(
        (x: { needs_category: boolean; mf_category: string | null }) =>
          !x.needs_category || x.mf_category === null,
      ),
    ).toBe(true);
    expect(detail.needs_category).toBe(true);
    expect(detail.mf_category).toBeNull();
  }],
  ["missing_prices", async () => {
    localStorage.setItem(STORAGE_KEY, "missing_prices");
    const [h, o, detail, ...seriesByWindow] = await Promise.all([
      fetch(`${API}/portfolio/holdings`).then((r) => r.json()),
      fetch(`${API}/portfolio/overview`).then((r) => r.json()),
      fetch(`${API}/portfolio/holdings/1`).then((r) => r.json()),
      ...(["ITD", "1Y", "3Y", "5Y"] as const).map((window) =>
        fetch(`${API}/portfolio/series?window=${window}`).then((r) => r.json()),
      ),
    ]);
    expect(h.holdings.every((x: { ltp: number | null }) => x.ltp === null)).toBe(
      true,
    );
    expect(
      h.holdings.every(
        (x: { value: number | null; absolute_pct: number | null }) =>
          x.value === null && x.absolute_pct === null,
      ),
    ).toBe(true);
    expect(o.incomplete).toBe(true);
    expect(o.total_value === 0 || o.total_value === null).toBe(true);
    expect(o.absolute).toMatchObject({
      current_value: 0,
      invested_cost: 77500,
      gain_inr: -77500,
      gain_pct: -1,
    });
    expect(o.allocation).toEqual([]);
    expect(
      seriesByWindow.every(
        (series: { available: boolean; points: unknown[] }) =>
          series.available === false && series.points.length === 0,
      ),
    ).toBe(true);
    expect(o.windows.ITD).toMatchObject({
      absolute_pct: null,
      absolute_inr: null,
      xirr: null,
      cagr: null,
      benchmark_return: null,
      absolute_excess_pp: null,
      xirr_excess_pp: null,
      cagr_excess_pp: null,
    });
    expect(o.windows["1Y"]).toMatchObject({
      absolute_pct: null,
      xirr: null,
      cagr: null,
      benchmark_return: null,
      absolute_excess_pp: null,
      xirr_excess_pp: null,
      cagr_excess_pp: null,
    });
    expect(detail).toMatchObject({
      ltp: null,
      value: null,
      absolute_pct: null,
      incomplete: true,
    });
  }],
  ["negative", async () => {
    localStorage.setItem(STORAGE_KEY, "negative");
    const o = await fetch(`${API}/portfolio/overview`).then((r) => r.json());
    expect(o.absolute.gain_inr).toBeLessThan(0);
    expect(o.absolute.gain_pct).toBeLessThan(0);
    expect(o.absolute_excess_pp).toBeLessThan(0);
    expect(o.xirr).toBeLessThan(0);
    expect(o.cagr).toBeLessThan(0);
    expect(o.windows.ITD?.absolute_pct).toBeLessThan(0);
    expect(o.windows.ITD?.xirr).toBeLessThan(0);
    expect(o.windows.ITD?.cagr).toBeLessThan(0);
    expect(o.windows.ITD?.xirr).not.toBe(0.15);
    expect(o.windows["1Y"]?.absolute_pct).toBeLessThan(0);
    expect(o.windows["1Y"]?.xirr).toBeLessThan(0);
    expect(o.windows["1Y"]?.cagr).toBeLessThan(0);
    expect(o.windows["1Y"]?.xirr_excess_pp).toBeLessThan(0);
  }],
] as const)("%s scenario fixture", async (_name, fn) => {
  await fn();
});

it("warns when scenario overlay is missing", () => {
  const warn = vi.spyOn(console, "warn").mockImplementation(() => {});

  loadFixture("gap", "overview");

  expect(warn).toHaveBeenCalled();
  warn.mockRestore();
});
