import {
  SCENARIO_IDS,
  getActiveScenario,
  setActiveScenario,
  STORAGE_KEY,
} from "@/mocks/scenarios";
import { fixtureModules } from "@/mocks/fixture-modules";
import { loadFixture } from "@/mocks/load-fixture";

describe("fixtureModules", () => {
  it("registers happy overview and missing_prices overlay keys", () => {
    expect(fixtureModules["./fixtures/happy/overview.json"]).toBeTruthy();
    expect(
      fixtureModules["./fixtures/missing_prices/overview.json"],
    ).toBeTruthy();
  });
});

it("lists all nine scenario ids", () => {
  expect(SCENARIO_IDS).toEqual([
    "happy",
    "empty",
    "logged_out",
    "stale",
    "gap",
    "import_errors",
    "unknown_category",
    "missing_prices",
    "negative",
  ]);
});

it("defaults to happy and persists selection", () => {
  localStorage.clear();
  expect(getActiveScenario()).toBe("happy");
  setActiveScenario("gap");
  expect(localStorage.getItem(STORAGE_KEY)).toBe("gap");
  expect(getActiveScenario()).toBe("gap");
});

it("merges scenario overlay onto happy fixture", () => {
  const auth = loadFixture<{ connected: boolean; last_sync_at: string | null }>(
    "logged_out",
    "auth-status",
  );
  expect(auth.connected).toBe(false);
  expect(auth.last_sync_at).toBeNull();
});
