import type { ImportResult } from "@/lib/api";

const KEY = "portfolio-tracker:last-import";

export function saveImportReport(report: ImportResult): void {
  if (typeof sessionStorage === "undefined") return;
  sessionStorage.setItem(KEY, JSON.stringify(report));
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function isNumberRecord(value: unknown): value is Record<string, number> {
  return (
    isRecord(value) &&
    Object.values(value).every(
      (item) => typeof item === "number" && Number.isFinite(item),
    )
  );
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isSingleImportResult(value: unknown): value is ImportResult {
  return (
    isRecord(value) &&
    value.format === "console_tradebook" &&
    typeof value.new === "number" &&
    Number.isFinite(value.new) &&
    typeof value.existing === "number" &&
    Number.isFinite(value.existing) &&
    isNumberRecord(value.segment_counts) &&
    isStringArray(value.flagged_rows) &&
    isNullableString(value.date_min) &&
    isNullableString(value.date_max) &&
    isStringArray(value.financial_years)
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
