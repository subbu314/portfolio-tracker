"use client";

import { useEffect, useMemo, useState } from "react";
import { HoldingsTable } from "@/components/HoldingsTable";
import { WindowSelect } from "@/components/WindowSelect";
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

  if (error) return <p role="alert">{error}</p>;
  if (!rows) return <p>Loading…</p>;

  return (
    <div className="stack">
      <div className="panel-head">
        <h1>Holdings</h1>
        <WindowSelect value={windowKey} onChange={setWindowKey} />
      </div>
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
    </div>
  );
}
