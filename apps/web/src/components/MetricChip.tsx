import { FormattedMetricValue } from "@/components/FormattedMetricValue";
import { Badge } from "@/components/ui/badge";

export function MetricChip({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="metric-card">
      <Badge variant="secondary">{label}</Badge>
      <FormattedMetricValue value={value} availableClassName="metric-value" />
    </div>
  );
}
