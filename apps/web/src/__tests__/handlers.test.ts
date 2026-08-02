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
