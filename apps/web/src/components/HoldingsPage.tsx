"use client";

import { useEffect, useMemo, useState } from "react";
import { EmptyState } from "@/components/EmptyState";
import { HoldingsTable } from "@/components/HoldingsTable";
import { WindowSelect } from "@/components/WindowSelect";
import { PageAlert } from "@/components/PageAlert";
import { PageSkeleton } from "@/components/PageSkeleton";
import { api, type Holding } from "@/lib/api";
import type { WindowKey } from "@/lib/windows";

export function HoldingsPage() {
  const [rows, setRows] = useState<Holding[] | null>(null);
  const [windowKey, setWindowKey] = useState<WindowKey>("ITD");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void api
      .getHoldings()
      .then(setRows)
      .catch((loadError: Error) => setError(loadError.message));
  }, []);

  const { equityEtfs, mfs } = useMemo(() => {
    const list = rows ?? [];
    return {
      equityEtfs: list.filter((holding) => holding.instrument_type !== "mf"),
      mfs: list.filter((holding) => holding.instrument_type === "mf"),
    };
  }, [rows]);

  if (error) return <PageAlert>{error}</PageAlert>;
  if (!rows) {
    return <PageSkeleton variant="holdings" />;
  }

  return (
    <div className="stack">
      <div className="panel-head">
        <h1>Holdings</h1>
        <WindowSelect value={windowKey} onChange={setWindowKey} />
      </div>
      {rows.length === 0 ? (
        <EmptyState
          title="No holdings yet"
          description="Refresh after logging in with Zerodha."
          action={{ label: "Open Settings", href: "/settings" }}
        />
      ) : (
        <>
          <HoldingsTable
            title="Stocks & ETFs"
            variant="equity"
            rows={equityEtfs}
            windowKey={windowKey}
          />
          <HoldingsTable
            title="Mutual funds"
            variant="mf"
            rows={mfs}
            windowKey={windowKey}
          />
        </>
      )}
    </div>
  );
}
