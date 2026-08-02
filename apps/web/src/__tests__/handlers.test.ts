import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, expect, it } from "vitest";
import { handlers } from "@/mocks/handlers";
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
    expect(s.available).toBe(false);
  }],
  ["logged_out", async () => {
    localStorage.setItem(STORAGE_KEY, "logged_out");
    const a = await fetch(`${API}/auth/status`).then((r) => r.json());
    expect(a.connected).toBe(false);
    expect(a.last_sync_at).toBeNull();
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
  ["import_errors", async () => {
    localStorage.setItem(STORAGE_KEY, "import_errors");
    const r = await fetch(`${API}/import/csv`, {
      method: "POST",
      body: new FormData(),
    }).then((x) => x.json());
    expect(r.flagged_rows.length).toBeGreaterThan(0);
    expect(r.existing).toBeGreaterThan(0);
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
    const [h, o] = await Promise.all([
      fetch(`${API}/portfolio/holdings`).then((r) => r.json()),
      fetch(`${API}/portfolio/overview`).then((r) => r.json()),
    ]);
    expect(
      h.holdings.some((x: { ltp: number | null }) => x.ltp === null),
    ).toBe(true);
    expect(
      h.holdings.some((x: { value: number | null }) => x.value === null),
    ).toBe(true);
    expect(
      [o.xirr, o.cagr, o.absolute.gain_pct].some((v) => v === null),
    ).toBe(true);
  }],
  ["negative", async () => {
    localStorage.setItem(STORAGE_KEY, "negative");
    const o = await fetch(`${API}/portfolio/overview`).then((r) => r.json());
    expect(o.absolute.gain_inr).toBeLessThan(0);
    expect(o.absolute.gain_pct).toBeLessThan(0);
    expect(o.absolute_excess_pp).toBeLessThan(0);
  }],
] as const)("%s scenario fixture", async (_name, fn) => {
  await fn();
});
