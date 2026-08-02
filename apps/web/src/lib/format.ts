export const UNAVAILABLE = "N/A";

export function isFiniteNumber(
  value: number | null | undefined,
): value is number {
  return value !== null && value !== undefined && Number.isFinite(value);
}

export function isUnavailable(value: string): boolean {
  return value === UNAVAILABLE;
}

export function unavailableClassName(
  value: string,
  whenAvailable: string,
): string {
  return isUnavailable(value)
    ? "font-mono tabular-nums text-muted-foreground"
    : whenAvailable;
}

export function formatInr(value: number | null | undefined): string {
  if (!isFiniteNumber(value)) return UNAVAILABLE;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatPrice(value: number | null | undefined): string {
  if (!isFiniteNumber(value)) return UNAVAILABLE;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(value);
}

export function formatPct(value: number | null | undefined): string {
  if (!isFiniteNumber(value)) return UNAVAILABLE;
  return `${(value * 100).toFixed(2)}%`;
}

export function formatPp(value: number | null | undefined): string {
  if (!isFiniteNumber(value)) return UNAVAILABLE;
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)} pp`;
}

export function formatSignedInr(value: number | null | undefined): string {
  if (!isFiniteNumber(value)) return UNAVAILABLE;
  if (value === 0) return formatInr(0);
  const sign = value > 0 ? "+" : "−";
  return `${sign}${formatInr(Math.abs(value))}`;
}
