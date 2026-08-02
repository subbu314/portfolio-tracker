import type { ImportResult } from "@/lib/api";

export type SingleImportResult = Extract<
  ImportResult,
  { format: "console_tradebook" }
>;

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

export function isSingleImportResult(
  value: unknown,
): value is SingleImportResult {
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
