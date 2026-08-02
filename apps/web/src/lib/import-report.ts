import type { ImportResult } from "@/lib/api";

const KEY = "portfolio-tracker:last-import";

export function saveImportReport(report: ImportResult): void {
  if (typeof sessionStorage === "undefined") return;
  sessionStorage.setItem(KEY, JSON.stringify(report));
}

function isSingleImportResult(value: unknown): value is ImportResult {
  return (
    typeof value === "object" &&
    value !== null &&
    "format" in value &&
    (value as { format: unknown }).format === "console_tradebook"
  );
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
