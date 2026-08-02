"use client";

import { useEffect, useState } from "react";
import { AllocationChart } from "@/components/AllocationChart";
import { MetricCard } from "@/components/MetricCard";
import { MetricWindowSelects } from "@/components/MetricWindowSelects";
import { PageAlert } from "@/components/PageAlert";
import { SeriesChartPanel } from "@/components/SeriesChartPanel";
import { StatusBanner } from "@/components/StatusBanner";
import { ValueHero } from "@/components/ValueHero";
import { Skeleton } from "@/components/ui/skeleton";
import { useCancellableQuery } from "@/hooks/useCancellableQuery";
import { allocationByKind } from "@/lib/allocation";
import {
  api,
  type Alerts,
  type AuthStatus,
  type Holding,
  type Overview,
} from "@/lib/api";
import { toPortfolioChartPoints } from "@/lib/series";
import { deriveStatusBanner, todayIst } from "@/lib/status";
import type { MetricKey, WindowKey } from "@/lib/windows";

export function OverviewPage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [auth, setAuth] = useState<AuthStatus | null>(null);
  const [alerts, setAlerts] = useState<Alerts | null>(null);
  const [chartMetric, setChartMetric] = useState<MetricKey>("absolute");
  const [chartWindow, setChartWindow] = useState<WindowKey>("ITD");
  const [pageError, setPageError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const {
    data: series,
    error: chartError,
  } = useCancellableQuery({
    key: [chartWindow],
    enabled: chartMetric === "absolute",
    queryFn: () => api.getPortfolioSeries(chartWindow),
  });

  async function loadCore() {
    const [nextOverview, nextHoldings, nextAuth, nextAlerts] =
      await Promise.all([
        api.getOverview(),
        api.getHoldings(),
        api.getAuthStatus(),
        api.getAlerts(),
      ]);
    setOverview(nextOverview);
    setHoldings(nextHoldings);
    setAuth(nextAuth);
    setAlerts(nextAlerts);
    setActionError(null);
  }

  useEffect(() => {
    void loadCore().catch((loadError: Error) =>
      setPageError(loadError.message),
    );
  }, []);

  async function onRefresh() {
    setRefreshing(true);
    try {
      await api.postSync();
      await loadCore();
    } catch (syncError) {
      setActionError(
        syncError instanceof Error ? syncError.message : "Sync failed",
      );
    } finally {
      setRefreshing(false);
    }
  }

  if (pageError && !overview) return <PageAlert>{pageError}</PageAlert>;
  if (!overview || !auth || !alerts) {
    return (
      <div className="stack" data-testid="page-skeleton">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-24 w-full" />
        <div className="grid gap-5 md:grid-cols-2">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
        <Skeleton className="h-80 w-full" />
      </div>
    );
  }

  const banner = deriveStatusBanner({
    connected: auth.connected,
    lastSyncAt: auth.last_sync_at,
    incomplete: overview.incomplete,
    gap: alerts.gap,
    today: todayIst(),
  });

  return (
    <div className="stack">
      <h1>Overview</h1>
      {actionError ? <PageAlert>{actionError}</PageAlert> : null}
      <StatusBanner
        model={banner}
        onRefresh={onRefresh}
        refreshing={refreshing}
      />
      <ValueHero
        totalValue={overview.total_value}
        investedCost={overview.absolute.invested_cost}
        gainInr={overview.absolute.gain_inr}
        gainPct={overview.absolute.gain_pct}
      />
      <div className="card-grid">
        <MetricCard
          title="Portfolio return"
          windows={overview.windows}
          mode="return"
          defaultMetric="xirr"
        />
        <MetricCard
          title="Outperformance"
          windows={overview.windows}
          mode="outperformance"
          defaultMetric="xirr"
        />
      </div>
      <section className="panel">
        <div className="panel-head">
          <h2>Portfolio vs category benchmarks</h2>
          <MetricWindowSelects
            idPrefix="chart"
            labelPrefix="Portfolio chart"
            metric={chartMetric}
            window={chartWindow}
            onMetricChange={setChartMetric}
            onWindowChange={setChartWindow}
          />
        </div>
        <SeriesChartPanel
          title="Portfolio vs category benchmarks"
          chartError={chartError}
          available={series?.available ?? false}
          loading={chartMetric === "absolute" && series === null}
          metricSupportsSeries={chartMetric === "absolute"}
          points={toPortfolioChartPoints(series)}
          portfolioLabel="Portfolio"
          benchmarkLabel="Category benchmarks (market-weighted)"
        />
      </section>
      <section className="panel">
        <h2>Asset allocation</h2>
        <AllocationChart
          slices={allocationByKind(holdings)}
          holdingsCount={holdings.length}
        />
      </section>
    </div>
  );
}
