import type { Holding } from "@/lib/api";

export type AllocationSliceUi = { label: string; weight: number };

export function allocationByKind(holdings: Holding[]): AllocationSliceUi[] {
  let equity = 0;
  let mf = 0;
  let etf = 0;
  for (const h of holdings) {
    const v = h.value ?? 0;
    if (h.instrument_type === "mf") mf += v;
    else if (h.instrument_type === "etf") etf += v;
    else equity += v;
  }
  const total = equity + mf + etf;
  if (!total) return [];
  return [
    { label: "Equity", weight: equity / total },
    { label: "Mutual funds", weight: mf / total },
    { label: "ETFs", weight: etf / total },
  ].filter((s) => s.weight > 0);
}
