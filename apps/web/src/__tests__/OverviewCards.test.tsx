import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MetricCard } from "@/components/MetricCard";
import { ReturnSeriesChart } from "@/components/ReturnSeriesChart";
import { ValueHero } from "@/components/ValueHero";

describe("ValueHero", () => {
  it("shows value, invested, and absolute return", () => {
    render(
      <ValueHero
        totalValue={250000}
        investedCost={200000}
        gainInr={50000}
        gainPct={0.25}
      />,
    );
    expect(screen.getByText(/total portfolio value/i)).toBeInTheDocument();
    expect(screen.getByText(/25\.00%/)).toBeInTheDocument();
  });

  it("shows N/A for null gain pct", () => {
    render(
      <ValueHero totalValue={0} investedCost={0} gainInr={0} gainPct={null} />,
    );
    const unavailableGain = screen.getAllByText("N/A")[0];
    expect(unavailableGain).toHaveClass("text-muted-foreground");
    expect(unavailableGain).not.toHaveClass("metric-percent");
  });
});

describe("MetricCard", () => {
  it("updates displayed value when Metric changes", async () => {
    const user = userEvent.setup();
    render(
      <MetricCard
        title="Portfolio return"
        windows={{
          ITD: {
            absolute_pct: 0.2,
            absolute_inr: 1,
            xirr: 0.18,
            cagr: 0.1,
            benchmark_return: 0.12,
            absolute_excess_pp: 1,
            xirr_excess_pp: 2,
            cagr_excess_pp: 3,
          },
          "1Y": null,
          "3Y": null,
          "5Y": null,
        }}
        mode="return"
        defaultMetric="xirr"
      />,
    );
    expect(screen.getByText("18.00%")).toBeInTheDocument();
    await user.click(screen.getByRole("combobox", { name: /metric/i }));
    await user.click(screen.getByRole("option", { name: "CAGR" }));
    expect(screen.getByText("10.00%")).toBeInTheDocument();
  });

  it("shows N/A without beat copy when outperformance is missing", () => {
    render(
      <MetricCard
        title="Outperformance"
        windows={{
          ITD: null,
          "1Y": null,
          "3Y": null,
          "5Y": null,
        }}
        mode="outperformance"
        defaultMetric="xirr"
      />,
    );
    const unavailableMetric = screen.getByText("N/A");
    expect(unavailableMetric).toHaveClass("text-muted-foreground");
    expect(unavailableMetric).not.toHaveClass("metric-value");
    expect(
      screen.queryByText(/you beat category benchmarks/i),
    ).not.toBeInTheDocument();
  });

  it("uses trailing copy with absolute magnitude for negative outperformance", () => {
    render(
      <MetricCard
        title="Outperformance"
        windows={{
          ITD: {
            absolute_pct: 0.08,
            absolute_inr: 1,
            xirr: 0.08,
            cagr: 0.08,
            benchmark_return: 0.1,
            absolute_excess_pp: -2,
            xirr_excess_pp: -2,
            cagr_excess_pp: -2,
          },
          "1Y": null,
          "3Y": null,
          "5Y": null,
        }}
        mode="outperformance"
        defaultMetric="xirr"
      />,
    );

    expect(
      screen.getByText("You trail category benchmarks by 2.00 pp"),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/you beat category benchmarks/i),
    ).not.toBeInTheDocument();
  });
});

describe("ReturnSeriesChart", () => {
  it("shows loading copy before series availability is known", () => {
    render(
      <ReturnSeriesChart
        title="Portfolio returns"
        available={false}
        loading
        metricSupportsSeries
        points={[]}
      />,
    );

    expect(document.querySelector(".animate-pulse")).toHaveClass(
      "h-[320px]",
      "w-full",
    );
    expect(
      screen.queryByText(/not enough history/i),
    ).not.toBeInTheDocument();
  });

  it("shows explicit N/A copy for unsupported metrics", () => {
    render(
      <ReturnSeriesChart
        title="Portfolio returns"
        available
        metricSupportsSeries={false}
        points={[]}
      />,
    );

    expect(
      screen.getByText(
        "N/A — series chart supports Absolute return only for v1.",
      ),
    ).toBeInTheDocument();
  });
});
