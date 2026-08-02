import { render, screen } from "@testing-library/react";
import { HoldingsTable } from "@/components/HoldingsTable";
import type { Holding } from "@/lib/api";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

const base = {
  qty: 2,
  avg_price: 100,
  ltp: 120,
  value: 240,
  absolute_pct: null,
  absolute_inr: null,
  xirr: null,
  cagr: null,
  benchmark: "Nifty 500",
  benchmark_return: null,
  absolute_excess_pp: null,
  xirr_excess_pp: null,
  cagr_excess_pp: null,
  incomplete: false,
  needs_category: false,
  mf_category: null,
  windows: {
    ITD: {
      absolute_pct: 0.1,
      absolute_inr: 20,
      xirr: 0.12,
      cagr: null,
      benchmark_return: 0.08,
      absolute_excess_pp: 2,
      xirr_excess_pp: 1.5,
      cagr_excess_pp: null,
    },
    "1Y": null,
    "3Y": null,
    "5Y": null,
  },
} as const;

describe("HoldingsTable", () => {
  it("renders Abs % XIRR CAGR Outperf and N/A for missing CAGR", () => {
    const rows: Holding[] = [
      {
        ...base,
        instrument_id: 1,
        symbol: "RELIANCE",
        instrument_type: "equity",
      },
    ];
    render(
      <HoldingsTable
        title="Stocks & ETFs"
        variant="equity"
        rows={rows}
        windowKey="ITD"
      />,
    );
    expect(screen.getByRole("link", { name: "RELIANCE" })).toHaveAttribute(
      "href",
      "/holdings/1",
    );
    expect(screen.getByText("10.00%")).toBeInTheDocument();
    expect(screen.getByText("12.00%")).toBeInTheDocument();
    expect(screen.getByText("N/A")).toBeInTheDocument(); // CAGR
    expect(screen.getByText("+2.00 pp")).toBeInTheDocument(); // absolute_excess_pp
  });
});
