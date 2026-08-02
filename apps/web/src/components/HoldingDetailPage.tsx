"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { PageAlert } from "@/components/PageAlert";
import { ReturnSeriesChart } from "@/components/ReturnSeriesChart";
import { TransactionsTable } from "@/components/TransactionsTable";
import { WindowSelect } from "@/components/WindowSelect";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  api,
  type Holding,
  type HoldingSeries,
  type HoldingTransactions,
} from "@/lib/api";
import { formatInr, formatPct, formatPp } from "@/lib/format";
import { getWindowMetrics, type WindowKey } from "@/lib/windows";

type Props = {
  instrumentId: number;
};

function ReturnChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-card">
      <Badge variant="secondary">{label}</Badge>
      <p className="metric-value">{value}</p>
    </div>
  );
}

export function HoldingDetailPage({ instrumentId }: Props) {
  const [holding, setHolding] = useState<Holding | null>(null);
  const [transactions, setTransactions] =
    useState<HoldingTransactions | null>(null);
  const [series, setSeries] = useState<HoldingSeries | null>(null);
  const [window, setWindow] = useState<WindowKey>("ITD");
  const [error, setError] = useState<string | null>(null);
  const [chartError, setChartError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    let cancelled = false;
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

  useEffect(() => {
    let cancelled = false;
    setSeries(null);
    setChartError(null);
    void api
      .getHoldingSeries(instrumentId, window)
      .then((nextSeries) => {
        if (!cancelled) setSeries(nextSeries);
      })
      .catch((loadError: Error) => {
        if (!cancelled) setChartError(loadError.message);
      });
    return () => {
      cancelled = true;
    };
  }, [instrumentId, window]);

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
    return (
      <div className="stack" data-testid="page-skeleton">
        <Skeleton className="h-5 w-36" />
        <Skeleton className="h-20 w-full" />
        <div className="grid gap-5 md:grid-cols-4">
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-28 w-full" />
        </div>
        <Skeleton className="h-80 w-full" />
      </div>
    );
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
          {formatInr(holding.avg_price)} · {priceLabel} {formatInr(holding.ltp)}
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
        <ReturnChip label="Abs %" value={formatPct(metrics?.absolute_pct)} />
        <ReturnChip label="XIRR" value={formatPct(metrics?.xirr)} />
        <ReturnChip label="CAGR" value={formatPct(metrics?.cagr)} />
        <ReturnChip
          label="Outperf."
          value={formatPp(metrics?.absolute_excess_pp)}
        />
      </section>
      <section className="panel">
        <h2>Holding vs mapped category benchmark</h2>
        {chartError ? (
          <PageAlert title="Chart unavailable">{chartError}</PageAlert>
        ) : (
          <ReturnSeriesChart
            title="Holding vs mapped category benchmark"
            available={series?.available ?? false}
            loading={series === null}
            metricSupportsSeries
            points={(series?.points ?? []).map((point) => ({
              date: point.date,
              portfolio: point.holding_return ?? null,
              benchmark: point.benchmark_return ?? null,
            }))}
            portfolioLabel={holding.symbol}
            benchmarkLabel={holding.benchmark}
          />
        )}
      </section>
      <TransactionsTable rows={transactions.transactions} />
    </div>
  );
}
