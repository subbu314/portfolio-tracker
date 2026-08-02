"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
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
import { formatInr, formatPct, formatPp, formatPrice } from "@/lib/format";
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
  const router = useRouter();

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
                  <TableRow
                    key={row.instrument_id}
                    className="cursor-pointer"
                    tabIndex={0}
                    aria-label={`Open ${row.symbol}`}
                    onClick={(event) => {
                      const target = event.target;
                      const isInteractiveTarget =
                        target instanceof Element &&
                        target.closest(
                          'a, button, input, select, textarea, summary, [role="button"], [role="link"], [contenteditable="true"]',
                        );

                      if (
                        isInteractiveTarget ||
                        event.metaKey ||
                        event.ctrlKey ||
                        event.altKey ||
                        event.shiftKey ||
                        event.button !== 0
                      ) {
                        return;
                      }

                      router.push(`/holdings/${row.instrument_id}`);
                    }}
                    onKeyDown={(event) => {
                      const target = event.target;
                      const isInteractiveTarget =
                        target instanceof Element &&
                        target.closest(
                          'a, button, input, select, textarea, summary, [role="button"], [role="link"], [contenteditable="true"]',
                        );

                      if (
                        !isInteractiveTarget &&
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
      </CardContent>
    </Card>
  );
}
