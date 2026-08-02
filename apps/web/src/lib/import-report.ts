import type { ImportResult } from "@/lib/api";
import { isSingleImportResult } from "@/lib/import-types";

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
    const parsed: unknown = JSON.parse(raw);
    return isSingleImportResult(parsed) ? parsed : null;
  } catch {
    return null;
  }
}
