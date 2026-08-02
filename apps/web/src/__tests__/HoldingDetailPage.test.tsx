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

it("shows skeleton while core holding data loads", () => {
  mocks.getHolding.mockReturnValue(new Promise(() => {}));
  mocks.getHoldingTransactions.mockReturnValue(new Promise(() => {}));
  mocks.getHoldingSeries.mockReturnValue(new Promise(() => {}));

  render(<HoldingDetailPage instrumentId={1} />);

  expect(screen.getByTestId("page-skeleton")).toBeInTheDocument();
  expect(screen.queryByText("Loading…")).not.toBeInTheDocument();
});

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
  expect(await screen.findByRole("alert")).toHaveTextContent("Series unavailable");
  expect(screen.getByText("N/A")).toHaveClass("text-muted-foreground");
});

it("clears notFound when navigating from missing id to valid id", async () => {
  mocks.getHolding
    .mockRejectedValueOnce(new Error("Holding not found"))
    .mockResolvedValueOnce({
      instrument_id: 2,
      symbol: "INFY",
      instrument_type: "equity",
      qty: 10,
      avg_price: 100,
      ltp: 110,
      value: 1100,
      absolute_pct: 0.1,
      absolute_inr: 100,
      xirr: 0.1,
      cagr: 0.1,
      benchmark: "Nifty IT",
      benchmark_return: 0.08,
      absolute_excess_pp: 2,
      xirr_excess_pp: 1,
      cagr_excess_pp: 1,
      incomplete: false,
      needs_category: false,
      mf_category: null,
      windows: {
        ITD: {
          absolute_pct: 0.1,
          absolute_inr: 100,
          xirr: 0.1,
          cagr: 0.1,
          benchmark_return: 0.08,
          absolute_excess_pp: 2,
          xirr_excess_pp: 1,
          cagr_excess_pp: 1,
        },
        "1Y": null,
        "3Y": null,
        "5Y": null,
      },
    });
  mocks.getHoldingTransactions.mockResolvedValue({
    instrument_id: 2,
    transactions: [],
  });
  mocks.getHoldingSeries.mockResolvedValue({
    available: false,
    points: [],
  });

  const { rerender } = render(<HoldingDetailPage instrumentId={999} />);
  expect(await screen.findByText(/Holding not found/i)).toBeInTheDocument();

  rerender(<HoldingDetailPage instrumentId={2} />);
  expect(await screen.findByText("INFY")).toBeInTheDocument();
  expect(screen.queryByText(/Holding not found/i)).not.toBeInTheDocument();
  expect(mocks.getHolding).toHaveBeenCalledWith(2);
});

it("clears stale holding data when navigating between valid ids", async () => {
  const holdingA = {
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
  };
  const holdingB = {
    instrument_id: 2,
    symbol: "INFY",
    instrument_type: "equity",
    qty: 10,
    avg_price: 100,
    ltp: 110,
    value: 1100,
    absolute_pct: 0.1,
    absolute_inr: 100,
    xirr: 0.1,
    cagr: 0.1,
    benchmark: "Nifty IT",
    benchmark_return: 0.08,
    absolute_excess_pp: 2,
    xirr_excess_pp: 1,
    cagr_excess_pp: 1,
    incomplete: false,
    needs_category: false,
    mf_category: null,
    windows: {
      ITD: {
        absolute_pct: 0.1,
        absolute_inr: 100,
        xirr: 0.1,
        cagr: 0.1,
        benchmark_return: 0.08,
        absolute_excess_pp: 2,
        xirr_excess_pp: 1,
        cagr_excess_pp: 1,
      },
      "1Y": null,
      "3Y": null,
      "5Y": null,
    },
  };

  let resolveHoldingB!: (value: typeof holdingB) => void;
  let resolveTransactionsB!: (value: {
    instrument_id: number;
    transactions: [];
  }) => void;

  mocks.getHolding
    .mockResolvedValueOnce(holdingA)
    .mockImplementationOnce(
      () => new Promise((resolve) => { resolveHoldingB = resolve; }),
    );
  mocks.getHoldingTransactions
    .mockResolvedValueOnce({ instrument_id: 1, transactions: [] })
    .mockImplementationOnce(
      () => new Promise((resolve) => { resolveTransactionsB = resolve; }),
    );
  mocks.getHoldingSeries.mockResolvedValue({
    available: false,
    points: [],
  });

  const { rerender } = render(<HoldingDetailPage instrumentId={1} />);
  expect(
    await screen.findByRole("heading", { name: "RELIANCE" }),
  ).toBeInTheDocument();

  rerender(<HoldingDetailPage instrumentId={2} />);

  expect(screen.queryByRole("heading", { name: "RELIANCE" })).not.toBeInTheDocument();
  expect(screen.getByTestId("page-skeleton")).toBeInTheDocument();

  resolveHoldingB(holdingB);
  resolveTransactionsB({ instrument_id: 2, transactions: [] });

  expect(
    await screen.findByRole("heading", { name: "INFY" }),
  ).toBeInTheDocument();
  expect(screen.queryByTestId("page-skeleton")).not.toBeInTheDocument();
});
