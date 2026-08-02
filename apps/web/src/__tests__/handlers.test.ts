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
    const h = await fetch(`${API}/portfolio/holdings`).then((r) => r.json());
    expect(h.holdings).toEqual([]);
  }],
  ["logged_out", async () => {
    localStorage.setItem(STORAGE_KEY, "logged_out");
    const a = await fetch(`${API}/auth/status`).then((r) => r.json());
    expect(a.connected).toBe(false);
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
  }],
  ["import_errors", async () => {
    localStorage.setItem(STORAGE_KEY, "import_errors");
    const r = await fetch(`${API}/import/csv`, {
      method: "POST",
      body: new FormData(),
    }).then((x) => x.json());
    expect(r.flagged_rows.length).toBeGreaterThan(0);
  }],
  ["unknown_category", async () => {
    localStorage.setItem(STORAGE_KEY, "unknown_category");
    const b = await fetch(`${API}/settings/benchmarks`).then((r) => r.json());
    expect(
      b.items.some((i: { needs_category: boolean }) => i.needs_category),
    ).toBe(true);
  }],
  ["missing_prices", async () => {
    localStorage.setItem(STORAGE_KEY, "missing_prices");
    const h = await fetch(`${API}/portfolio/holdings`).then((r) => r.json());
    expect(
      h.holdings.some((x: { ltp: number | null }) => x.ltp === null),
    ).toBe(true);
  }],
  ["negative", async () => {
    localStorage.setItem(STORAGE_KEY, "negative");
    const o = await fetch(`${API}/portfolio/overview`).then((r) => r.json());
    expect(o.absolute.gain_inr).toBeLessThan(0);
  }],
] as const)("%s scenario fixture", async (_name, fn) => {
  await fn();
});
