export const SCENARIO_IDS = [
  "happy",
  "empty",
  "logged_out",
  "stale",
  "gap",
  "import_errors",
  "unknown_category",
  "missing_prices",
  "negative",
] as const;

export type ScenarioId = (typeof SCENARIO_IDS)[number];

export const SCENARIO_LABELS: Record<ScenarioId, string> = {
  happy: "Happy",
  empty: "Empty",
  logged_out: "Logged out",
  stale: "Stale",
  gap: "Gap",
  import_errors: "Import errors",
  unknown_category: "Unknown category",
  missing_prices: "Missing prices",
  negative: "Negative",
};

export const STORAGE_KEY = "pt.mockScenario";

export function getActiveScenario(): ScenarioId {
  if (typeof window === "undefined") return "happy";
  const scenario = window.localStorage.getItem(STORAGE_KEY);
  if ((SCENARIO_IDS as readonly string[]).includes(scenario ?? "")) {
    return scenario as ScenarioId;
  }
  return "happy";
}

export function setActiveScenario(id: ScenarioId): void {
  window.localStorage.setItem(STORAGE_KEY, id);
}
