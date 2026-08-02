import type { ScenarioId } from "./scenarios";
import { fixtureModules } from "./fixture-modules";

function deepMerge<T>(base: T, overlay: unknown): T {
  if (overlay === undefined) return base;
  if (overlay === null) return null as T;
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

function fixtureKey(scenario: string, name: string): string {
  return `./fixtures/${scenario}/${name}.json`;
}

export function loadFixture<T>(scenario: ScenarioId, name: string): T {
  const base = fixtureModules[fixtureKey("happy", name)];
  const overlay = fixtureModules[fixtureKey(scenario, name)];
  if (base === undefined && overlay !== undefined) {
    return structuredClone(overlay) as T;
  }
  if (base === undefined) throw new Error(`Missing happy fixture: ${name}.json`);
  if (scenario === "happy") return structuredClone(base) as T;

  if (overlay === undefined) {
    if (process.env.NODE_ENV !== "production") {
      console.warn(
        `[mocks] missing overlay fixtures/${scenario}/${name}.json; using happy`,
      );
    }
    return structuredClone(base) as T;
  }

  return deepMerge(structuredClone(base) as T, overlay);
}
