export type GlossaryTermDefinition = {
  id: string;
  title: string;
  body: string;
};

export const GLOSSARY_TERMS: GlossaryTermDefinition[] = [
  {
    id: "absolute-return",
    title: "Absolute return",
    body: "Absolute return is the total percentage gain or loss compared with the amount invested. It is not annualised, so it is best read alongside the selected time period.",
  },
  {
    id: "xirr",
    title: "XIRR",
    body: "XIRR is an annualised return that accounts for the exact dates and amounts of cash flowing in and out. It is useful when investments were bought or sold at different times.",
  },
  {
    id: "cagr",
    title: "CAGR",
    body: "CAGR is the annual compounded growth rate between a starting value and an ending value. It describes a smooth yearly rate and does not account for cash flows during the period.",
  },
  {
    id: "outperformance",
    title: "Outperformance (pp)",
    body: "Outperformance is your portfolio return minus the return of its market-weighted category benchmarks. It is shown in percentage points (pp), so 12% versus 9% is 3 pp of outperformance.",
  },
  {
    id: "window",
    title: "Window",
    body: "Window is the period used to calculate returns: ITD (inception to date), 1Y (one year), 3Y (three years), or 5Y (five years). Changing it affects return metrics and comparisons, not today's portfolio value.",
  },
  {
    id: "ltp",
    title: "LTP",
    body: "LTP means last traded price, the latest available market price for a stock or ETF. It is used to estimate current value and may be stale when the market is closed or data is delayed.",
  },
  {
    id: "nav",
    title: "NAV",
    body: "NAV means net asset value, the per-unit value published by a mutual fund. It is used to estimate a fund holding's current value and is usually updated once per trading day.",
  },
  {
    id: "benchmark",
    title: "Benchmark / category index",
    body: "A benchmark is a market index used as a reference for an investment category, such as a broad equity or mid-cap index. Portfolio comparisons combine category benchmarks according to each holding's market value.",
  },
];
