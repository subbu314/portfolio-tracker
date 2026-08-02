"use client";

import {
  METRIC_KEYS,
  metricLabel,
  type MetricKey,
  type WindowKey,
} from "@/lib/windows";
import { WindowSelect } from "@/components/WindowSelect";

type Props = {
  metric: MetricKey;
  window: WindowKey;
  onMetricChange: (m: MetricKey) => void;
  onWindowChange: (w: WindowKey) => void;
};

export function MetricWindowSelects({
  metric,
  window,
  onMetricChange,
  onWindowChange,
}: Props) {
  return (
    <div className="control-row">
      <label className="field">
        <span>Metric</span>
        <select
          aria-label="Metric"
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
      <WindowSelect value={window} onChange={onWindowChange} />
    </div>
  );
}
