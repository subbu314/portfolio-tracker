"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { MetricChip } from "@/components/MetricChip";
import { PageAlert } from "@/components/PageAlert";
import { SeriesChartPanel } from "@/components/SeriesChartPanel";
import { TransactionsTable } from "@/components/TransactionsTable";
import { WindowSelect } from "@/components/WindowSelect";
import { PageSkeleton } from "@/components/PageSkeleton";
import { useCancellableQuery } from "@/hooks/useCancellableQuery";
import {
  api,
  type Holding,
  type HoldingTransactions,
} from "@/lib/api";
import { formatPct, formatPp, formatPrice } from "@/lib/format";
import { toHoldingChartPoints } from "@/lib/series";
import { getWindowMetrics, type WindowKey } from "@/lib/windows";

type Props = {
  instrumentId: number;
};

export function HoldingDetailPage({ instrumentId }: Props) {
  const [holding, setHolding] = useState<Holding | null>(null);
  const [transactions, setTransactions] =
    useState<HoldingTransactions | null>(null);
  const [window, setWindow] = useState<WindowKey>("ITD");
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const {
    data: series,
    error: chartError,
  } = useCancellableQuery({
    key: [instrumentId, window],
    queryFn: () => api.getHoldingSeries(instrumentId, window),
  });

  useEffect(() => {
    let cancelled = false;
    setHolding(null);
    setTransactions(null);
    setNotFound(false);
    setError(null);
    void Promise.all([
      api.getHolding(instrumentId),
      api.getHoldingTransactions(instrumentId),
    ])
      .then(([nextHolding, nextTransactions]) => {
        if (cancelled) return;
        setHolding(nextHolding);
        setTransactions(nextTransactions);
      })
      .catch((loadError: Error) => {
        if (cancelled) return;
        if (/not found/i.test(loadError.message)) setNotFound(true);
        else setError(loadError.message);
      });
    return () => {
      cancelled = true;
    };
  }, [instrumentId]);

  if (notFound) {
    return (
      <div className="stack">
        <PageAlert title="Holding not found">
          This holding is unavailable.
        </PageAlert>
        <Link className="text-accent underline underline-offset-4" href="/holdings">
          ← Back to Holdings
        </Link>
      </div>
    );
  }
  if (error) return <PageAlert>{error}</PageAlert>;
  if (!holding || !transactions) {
    return <PageSkeleton variant="holding-detail" />;
  }

  const metrics = getWindowMetrics(holding.windows, window);
  const priceLabel = holding.instrument_type === "mf" ? "NAV" : "LTP";

  return (
    <div className="stack">
      <Link className="text-accent underline underline-offset-4" href="/holdings">
        ← Back to Holdings
      </Link>
      <header>
        <h1>{holding.symbol}</h1>
        <p className="muted">
          {holding.instrument_type} · Qty {holding.qty} · Avg{" "}
          {formatPrice(holding.avg_price)} · {priceLabel} {formatPrice(holding.ltp)}
        </p>
        <p>
          Mapped benchmark: {holding.benchmark}.{" "}
          <span className="muted">Wrong benchmark? Fix in Settings.</span>
        </p>
      </header>
      <div className="control-row">
        <WindowSelect
          value={window}
          onChange={setWindow}
          id="holding-window"
          ariaLabel="Holding return window"
        />
      </div>
      <section className="card-grid" aria-label="Holding returns">
        <MetricChip label="Abs %" value={formatPct(metrics?.absolute_pct)} />
        <MetricChip label="XIRR" value={formatPct(metrics?.xirr)} />
        <MetricChip label="CAGR" value={formatPct(metrics?.cagr)} />
        <MetricChip
          label="Outperf."
          value={formatPp(metrics?.absolute_excess_pp)}
        />
      </section>
      <section className="panel">
        <h2>Holding vs mapped category benchmark</h2>
        <SeriesChartPanel
          title="Holding vs mapped category benchmark"
          chartError={chartError}
          available={series?.available ?? false}
          loading={series === null}
          metricSupportsSeries
          points={toHoldingChartPoints(series)}
          portfolioLabel={holding.symbol}
          benchmarkLabel={holding.benchmark}
        />
      </section>
      <TransactionsTable rows={transactions.transactions} />
    </div>
  );
}
