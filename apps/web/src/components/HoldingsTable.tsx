"use client";

import Link from "next/link";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Holding } from "@/lib/api";
import { formatInr, formatPct, formatPp } from "@/lib/format";
import { getWindowMetrics, type WindowKey } from "@/lib/windows";

type Props = {
  title: string;
  variant: "equity" | "mf";
  rows: Holding[];
  windowKey: WindowKey;
};

function FormattedTableCell({ value }: { value: string }) {
  return (
    <TableCell
      className={
        value === "N/A" ? "font-mono tabular-nums text-muted-foreground" : undefined
      }
    >
      {value}
    </TableCell>
  );
}

export function HoldingsTable({ title, variant, rows, windowKey }: Props) {
  return (
    <Card>
      <CardHeader className="p-5 pb-0">
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="p-5 pt-4">
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
              <TableRow>
                <TableCell
                  className="py-8 text-center text-muted-foreground"
                  colSpan={variant === "mf" ? 10 : 9}
                >
                  No rows
                </TableCell>
              </TableRow>
            ) : (
              rows.map((row) => {
                const metrics = getWindowMetrics(row.windows, windowKey);

                return (
                  <TableRow key={row.instrument_id}>
                    <TableCell>
                      <Link href={`/holdings/${row.instrument_id}`}>
                        {row.symbol}
                      </Link>
                    </TableCell>
                    {variant === "mf" && (
                      <TableCell>{row.mf_category ?? "—"}</TableCell>
                    )}
                    <TableCell>{row.qty}</TableCell>
                    <FormattedTableCell value={formatInr(row.avg_price)} />
                    <FormattedTableCell value={formatInr(row.ltp)} />
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
      </CardContent>
    </Card>
  );
}
