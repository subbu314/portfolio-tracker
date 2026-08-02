import { PageAlert } from "@/components/PageAlert";
import { ReturnSeriesChart } from "@/components/ReturnSeriesChart";
import type { SeriesChartPoint } from "@/lib/series";

type Props = {
  title: string;
  chartError: string | null;
  available: boolean;
  loading: boolean;
  metricSupportsSeries: boolean;
  points: SeriesChartPoint[];
  portfolioLabel: string;
  benchmarkLabel: string;
};

export function SeriesChartPanel({
  title,
  chartError,
  available,
  loading,
  metricSupportsSeries,
  points,
  portfolioLabel,
  benchmarkLabel,
}: Props) {
  if (chartError) {
    return <PageAlert title="Chart unavailable">{chartError}</PageAlert>;
  }

  return (
    <ReturnSeriesChart
      title={title}
      available={available}
      loading={loading}
      metricSupportsSeries={metricSupportsSeries}
      points={points}
      portfolioLabel={portfolioLabel}
      benchmarkLabel={benchmarkLabel}
    />
  );
}
