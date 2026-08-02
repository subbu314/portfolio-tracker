import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { WindowSelect } from "@/components/WindowSelect";
import { MetricWindowSelects } from "@/components/MetricWindowSelects";

describe("WindowSelect", () => {
  it("calls onChange with window key", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<WindowSelect value="ITD" onChange={onChange} />);
    await user.selectOptions(screen.getByLabelText(/window/i), "1Y");
    expect(onChange).toHaveBeenCalledWith("1Y");
  });
});

describe("MetricWindowSelects", () => {
  it("emits metric and window changes", async () => {
    const user = userEvent.setup();
    const onMetric = vi.fn();
    const onWindow = vi.fn();
    render(
      <MetricWindowSelects
        metric="xirr"
        window="ITD"
        onMetricChange={onMetric}
        onWindowChange={onWindow}
      />,
    );
    await user.selectOptions(screen.getByLabelText(/metric/i), "cagr");
    expect(onMetric).toHaveBeenCalledWith("cagr");
    await user.selectOptions(screen.getByLabelText(/window/i), "3Y");
    expect(onWindow).toHaveBeenCalledWith("3Y");
  });

  it("uses unique ids and labels for multiple control groups", () => {
    const onMetric = vi.fn();
    const onWindow = vi.fn();
    render(
      <>
        <MetricWindowSelects
          idPrefix="return"
          labelPrefix="Portfolio return"
          metric="xirr"
          window="ITD"
          onMetricChange={onMetric}
          onWindowChange={onWindow}
        />
        <MetricWindowSelects
          idPrefix="outperf"
          labelPrefix="Outperformance"
          metric="xirr"
          window="ITD"
          onMetricChange={onMetric}
          onWindowChange={onWindow}
        />
      </>,
    );

    expect(screen.getByLabelText("Portfolio return metric")).toHaveAttribute(
      "id",
      "return-metric",
    );
    expect(screen.getByLabelText("Portfolio return window")).toHaveAttribute(
      "id",
      "return-window",
    );
    expect(screen.getByLabelText("Outperformance metric")).toHaveAttribute(
      "id",
      "outperf-metric",
    );
    expect(screen.getByLabelText("Outperformance window")).toHaveAttribute(
      "id",
      "outperf-window",
    );
  });
});
