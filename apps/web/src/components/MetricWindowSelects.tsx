"use client";

import {
  METRIC_KEYS,
  metricLabel,
  type MetricKey,
  type WindowKey,
} from "@/lib/windows";
import { WindowSelect } from "@/components/WindowSelect";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

type Props = {
  idPrefix?: string;
  labelPrefix?: string;
  metric: MetricKey;
  window: WindowKey;
  onMetricChange: (m: MetricKey) => void;
  onWindowChange: (w: WindowKey) => void;
};

export function MetricWindowSelects({
  idPrefix = "performance",
  labelPrefix = "",
  metric,
  window,
  onMetricChange,
  onWindowChange,
}: Props) {
  const metricLabelText = labelPrefix ? `${labelPrefix} metric` : "Metric";
  const windowLabelText = labelPrefix ? `${labelPrefix} window` : "Window";

  return (
    <div className="control-row">
      <div className="flex flex-col gap-1.5 text-sm">
        <span
          id={`${idPrefix}-metric-label`}
          className="text-muted-foreground"
        >
          Metric
        </span>
        <Select
          value={metric}
          onValueChange={(nextMetric) =>
            onMetricChange(nextMetric as MetricKey)
          }
        >
          <SelectTrigger
            id={`${idPrefix}-metric`}
            aria-label={metricLabelText}
            className="min-w-[7rem]"
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {METRIC_KEYS.map((key) => (
              <SelectItem key={key} value={key}>
                {metricLabel(key)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <WindowSelect
        value={window}
        onChange={onWindowChange}
        id={`${idPrefix}-window`}
        ariaLabel={windowLabelText}
      />
    </div>
  );
}
