import type { ScenarioId } from "./scenarios";

function deepMerge<T>(base: T, overlay: unknown): T {
  if (overlay === null || overlay === undefined) return base;
  if (Array.isArray(overlay)) return overlay as T;
  if (typeof base !== "object" || base === null || typeof overlay !== "object") {
    return overlay as T;
  }

  const merged: Record<string, unknown> = {
    ...(base as Record<string, unknown>),
  };
  for (const [key, value] of Object.entries(overlay as Record<string, unknown>)) {
    merged[key] = key in merged ? deepMerge(merged[key], value) : value;
  }
  return merged as T;
}

const happyModules = import.meta.glob("./fixtures/happy/*.json", {
  eager: true,
  import: "default",
}) as Record<string, unknown>;

const overlayModules = import.meta.glob("./fixtures/*/*.json", {
  eager: true,
  import: "default",
}) as Record<string, unknown>;

function fixtureKey(scenario: string, name: string): string {
  return `./fixtures/${scenario}/${name}.json`;
}

export function loadFixture<T>(scenario: ScenarioId, name: string): T {
  const base = happyModules[fixtureKey("happy", name)];
  if (base === undefined) throw new Error(`Missing happy fixture: ${name}.json`);
  if (scenario === "happy") return structuredClone(base) as T;

  const overlay = overlayModules[fixtureKey(scenario, name)];
  return overlay === undefined
    ? (structuredClone(base) as T)
    : deepMerge(structuredClone(base), overlay);
}
