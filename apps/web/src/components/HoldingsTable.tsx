"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { DataTableCard } from "@/components/table/DataTableCard";
import { EmptyTableRow } from "@/components/table/EmptyTableRow";
import { FormattedTableCell } from "@/components/table/FormattedTableCell";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Holding } from "@/lib/api";
import { formatInr, formatPct, formatPp, formatPrice } from "@/lib/format";
import {
  isInteractiveEventTarget,
  shouldIgnoreRowClick,
} from "@/lib/table-row-nav";
import { getWindowMetrics, type WindowKey } from "@/lib/windows";

type Props = {
  title: string;
  variant: "equity" | "mf";
  rows: Holding[];
  windowKey: WindowKey;
};

export function HoldingsTable({ title, variant, rows, windowKey }: Props) {
  const router = useRouter();
  const colSpan = variant === "mf" ? 10 : 9;

  return (
    <DataTableCard title={title}>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Symbol</TableHead>
            {variant === "mf" && <TableHead>Category</TableHead>}
            <TableHead>Qty</TableHead>
            <TableHead>Avg</TableHead>
            <TableHead>{variant === "mf" ? "NAV" : "LTP"}</TableHead>
            <TableHead>Value</TableHead>
            <TableHead>Abs %</TableHead>
            <TableHead>XIRR</TableHead>
            <TableHead>CAGR</TableHead>
            <TableHead>Outperf. (pp)</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.length === 0 ? (
            <EmptyTableRow colSpan={colSpan} />
          ) : (
            rows.map((row) => {
              const metrics = getWindowMetrics(row.windows, windowKey);

              return (
                <TableRow
                  key={row.instrument_id}
                  className="cursor-pointer"
                  tabIndex={0}
                  aria-label={`Open ${row.symbol}`}
                  onClick={(event) => {
                    if (shouldIgnoreRowClick(event)) return;
                    router.push(`/holdings/${row.instrument_id}`);
                  }}
                  onKeyDown={(event) => {
                    if (
                      !isInteractiveEventTarget(event.target) &&
                      (event.key === "Enter" || event.key === " ")
                    ) {
                      event.preventDefault();
                      router.push(`/holdings/${row.instrument_id}`);
                    }
                  }}
                >
                  <TableCell>
                    <Link href={`/holdings/${row.instrument_id}`}>
                      {row.symbol}
                    </Link>
                  </TableCell>
                  {variant === "mf" && (
                    <TableCell>{row.mf_category ?? "—"}</TableCell>
                  )}
                  <TableCell>{row.qty}</TableCell>
                  <FormattedTableCell value={formatPrice(row.avg_price)} />
                  <FormattedTableCell value={formatPrice(row.ltp)} />
                  <FormattedTableCell value={formatInr(row.value)} />
                  <FormattedTableCell value={formatPct(metrics?.absolute_pct)} />
                  <FormattedTableCell value={formatPct(metrics?.xirr)} />
                  <FormattedTableCell value={formatPct(metrics?.cagr)} />
                  <FormattedTableCell
                    value={formatPp(metrics?.absolute_excess_pp)}
                  />
                </TableRow>
              );
            })
          )}
        </TableBody>
      </Table>
    </DataTableCard>
  );
}
