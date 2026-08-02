import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HoldingsTable } from "@/components/HoldingsTable";
import { makeHolding, makeWindows } from "@/__tests__/fixtures/holdings";

const mocks = vi.hoisted(() => ({
  push: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mocks.push }),
}));

const base = makeHolding({
  absolute_pct: null,
  absolute_inr: null,
  xirr: null,
  cagr: null,
  benchmark_return: null,
  absolute_excess_pp: null,
  xirr_excess_pp: null,
  cagr_excess_pp: null,
  windows: makeWindows({
    absolute_pct: 0.1,
    absolute_inr: 20,
    xirr: 0.12,
    cagr: null,
    benchmark_return: 0.08,
    absolute_excess_pp: 2,
    xirr_excess_pp: 1.5,
    cagr_excess_pp: null,
  }),
});

describe("HoldingsTable", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders Abs % XIRR CAGR Outperf and N/A for missing CAGR", () => {
    const rows = [
      {
        ...base,
        instrument_id: 1,
        symbol: "RELIANCE",
        instrument_type: "equity" as const,
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
    expect(screen.getByText("N/A")).toHaveClass("text-muted-foreground"); // CAGR
    expect(screen.getByText("+2.00 pp")).toBeInTheDocument(); // absolute_excess_pp
  });

  it("navigates to holding detail when the row is activated", async () => {
    const user = userEvent.setup();
    const rows = [
      {
        ...base,
        instrument_id: 1,
        symbol: "RELIANCE",
        instrument_type: "equity" as const,
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

    await user.click(screen.getByRole("row", { name: /RELIANCE/i }));
    expect(mocks.push).toHaveBeenCalledWith("/holdings/1");
  });

  it.each(["Enter", " "])(
    "navigates to holding detail when the row receives %j",
    (key) => {
      const rows = [
        {
          ...base,
          instrument_id: 1,
          symbol: "RELIANCE",
          instrument_type: "equity" as const,
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

      fireEvent.keyDown(screen.getByRole("row", { name: /RELIANCE/i }), {
        key,
      });
      expect(mocks.push).toHaveBeenCalledWith("/holdings/1");
    },
  );

  it("lets the symbol link handle its own navigation", () => {
    const rows = [
      {
        ...base,
        instrument_id: 1,
        symbol: "RELIANCE",
        instrument_type: "equity" as const,
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

    const link = screen.getByRole("link", { name: "RELIANCE" });
    link.addEventListener("click", (event) => event.preventDefault());

    fireEvent.click(link);
    expect(mocks.push).not.toHaveBeenCalled();
  });

  it.each([
    { key: "Enter" },
    { key: "Enter", metaKey: true },
    { key: "Enter", ctrlKey: true },
  ])("lets the symbol link handle keydown: %o", (keyInit) => {
    const rows = [
      {
        ...base,
        instrument_id: 1,
        symbol: "RELIANCE",
        instrument_type: "equity" as const,
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

    fireEvent.keyDown(screen.getByRole("link", { name: "RELIANCE" }), keyInit);
    expect(mocks.push).not.toHaveBeenCalled();
  });

  it.each([
    { metaKey: true },
    { ctrlKey: true },
    { altKey: true },
    { shiftKey: true },
    { button: 1 },
  ])("ignores modified and non-primary row clicks: %o", (clickInit) => {
    const rows = [
      {
        ...base,
        instrument_id: 1,
        symbol: "RELIANCE",
        instrument_type: "equity" as const,
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

    fireEvent.click(
      screen.getByRole("row", { name: /RELIANCE/i }),
      clickInit,
    );
    expect(mocks.push).not.toHaveBeenCalled();
  });
});
