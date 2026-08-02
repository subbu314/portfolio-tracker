"use client";

import Link from "next/link";
import type { Holding } from "@/lib/api";
import { formatInr, formatPct, formatPp } from "@/lib/format";
import { getWindowMetrics, type WindowKey } from "@/lib/windows";

type Props = {
  title: string;
  variant: "equity" | "mf";
  rows: Holding[];
  windowKey: WindowKey;
};

export function HoldingsTable({ title, variant, rows, windowKey }: Props) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            {variant === "mf" && <th>Category</th>}
            <th>Qty</th>
            <th>Avg</th>
            <th>{variant === "mf" ? "NAV" : "LTP"}</th>
            <th>Value</th>
            <th>Abs %</th>
            <th>XIRR</th>
            <th>CAGR</th>
            <th>Outperf. (pp)</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const metrics = getWindowMetrics(row.windows, windowKey);

            return (
              <tr key={row.instrument_id}>
                <td>
                  <Link href={`/holdings/${row.instrument_id}`}>
                    {row.symbol}
                  </Link>
                </td>
                {variant === "mf" && <td>{row.mf_category ?? "—"}</td>}
                <td>{row.qty}</td>
                <td>{formatInr(row.avg_price)}</td>
                <td>{formatInr(row.ltp)}</td>
                <td>{formatInr(row.value)}</td>
                <td>{formatPct(metrics?.absolute_pct)}</td>
                <td>{formatPct(metrics?.xirr)}</td>
                <td>{formatPct(metrics?.cagr)}</td>
                <td>{formatPp(metrics?.absolute_excess_pp)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
