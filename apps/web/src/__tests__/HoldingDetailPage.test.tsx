import { render, screen } from "@testing-library/react";
import { HoldingDetailPage } from "@/components/HoldingDetailPage";

const mocks = vi.hoisted(() => ({
  getHolding: vi.fn(),
  getHoldingTransactions: vi.fn(),
  getHoldingSeries: vi.fn(),
}));

vi.mock("@/lib/api", () => ({ api: mocks }));
vi.mock("@/components/ReturnSeriesChart", () => ({
  ReturnSeriesChart: () => <p>Return chart</p>,
}));
vi.mock("@/components/TransactionsTable", () => ({
  TransactionsTable: () => <p>Transactions</p>,
}));

it("keeps holding details visible when chart loading fails", async () => {
  mocks.getHolding.mockResolvedValue({
    instrument_id: 1,
    symbol: "RELIANCE",
    instrument_type: "equity",
    qty: 2,
    avg_price: 100,
    ltp: 120,
    value: 240,
    absolute_pct: 0.2,
    absolute_inr: 40,
    xirr: 0.15,
    cagr: null,
    benchmark: "Nifty 500",
    benchmark_return: 0.1,
    absolute_excess_pp: 10,
    xirr_excess_pp: 5,
    cagr_excess_pp: null,
    incomplete: false,
    needs_category: false,
    mf_category: null,
    windows: {
      ITD: {
        absolute_pct: 0.2,
        absolute_inr: 40,
        xirr: 0.15,
        cagr: null,
        benchmark_return: 0.1,
        absolute_excess_pp: 10,
        xirr_excess_pp: 5,
        cagr_excess_pp: null,
      },
      "1Y": null,
      "3Y": null,
      "5Y": null,
    },
  });
  mocks.getHoldingTransactions.mockResolvedValue({
    instrument_id: 1,
    transactions: [],
  });
  mocks.getHoldingSeries.mockRejectedValue(new Error("Series unavailable"));

  render(<HoldingDetailPage instrumentId={1} />);

  expect(
    await screen.findByRole("heading", { name: "RELIANCE" }),
  ).toBeInTheDocument();
  expect(await screen.findByText("Series unavailable")).toHaveAttribute(
    "role",
    "alert",
  );
});
