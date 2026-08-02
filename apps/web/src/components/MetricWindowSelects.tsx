"use client";

import {
  METRIC_KEYS,
  metricLabel,
  type MetricKey,
  type WindowKey,
} from "@/lib/windows";
import { WindowSelect } from "@/components/WindowSelect";

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
      <label className="field">
        <span>Metric</span>
        <select
          id={`${idPrefix}-metric`}
          aria-label={metricLabelText}
          value={metric}
          onChange={(e) => onMetricChange(e.target.value as MetricKey)}
        >
          {METRIC_KEYS.map((k) => (
            <option key={k} value={k}>
              {metricLabel(k)}
            </option>
          ))}
        </select>
      </label>
      <WindowSelect
        value={window}
        onChange={onWindowChange}
        id={`${idPrefix}-window`}
        ariaLabel={windowLabelText}
      />
    </div>
  );
}
