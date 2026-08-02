import type { Holding } from "@/lib/api";

export type AllocationSliceUi = { label: string; weight: number };

export function allocationByKind(holdings: Holding[]): AllocationSliceUi[] {
  let equity = 0;
  let mf = 0;
  let etf = 0;
  let other = 0;
  for (const h of holdings) {
    if (h.value == null) continue;
    if (h.instrument_type === "mf") mf += h.value;
    else if (h.instrument_type === "etf") etf += h.value;
    else if (h.instrument_type === "equity") equity += h.value;
    else other += h.value;
  }
  const total = equity + mf + etf + other;
  if (!total) return [];
  return [
    { label: "Equity", weight: equity / total },
    { label: "Mutual funds", weight: mf / total },
    { label: "ETFs", weight: etf / total },
    { label: "Other", weight: other / total },
  ].filter((s) => s.weight > 0);
}
