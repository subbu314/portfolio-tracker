import { render, screen } from "@testing-library/react";
import { FormattedMetricValue } from "@/components/FormattedMetricValue";
import { MetricChip } from "@/components/MetricChip";

it("mutes N/A metric values", () => {
  render(
    <FormattedMetricValue value="N/A" availableClassName="metric-value" />,
  );
  expect(screen.getByText("N/A")).toHaveClass("text-muted-foreground");
});

it("keeps available class for real values", () => {
  render(
    <FormattedMetricValue
      value="12.00%"
      availableClassName="metric-value font-mono tabular-nums"
    />,
  );
  expect(screen.getByText("12.00%")).toHaveClass("metric-value");
});

it("renders MetricChip label and muted N/A", () => {
  render(<MetricChip label="XIRR" value="N/A" />);
  expect(screen.getByText("XIRR")).toBeInTheDocument();
  expect(screen.getByText("N/A")).toHaveClass("text-muted-foreground");
});
