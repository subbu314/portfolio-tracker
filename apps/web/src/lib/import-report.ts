import type { ImportResult } from "@/lib/api";

const KEY = "portfolio-tracker:last-import";

export function saveImportReport(report: ImportResult): void {
  if (typeof sessionStorage === "undefined") return;
  sessionStorage.setItem(KEY, JSON.stringify(report));
}

export function loadImportReport(): ImportResult | null {
  if (typeof sessionStorage === "undefined") return null;
  const raw = sessionStorage.getItem(KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as ImportResult;
  } catch {
    return null;
  }
}
