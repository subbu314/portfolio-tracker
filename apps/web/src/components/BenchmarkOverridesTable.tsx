"use client";

import type { BenchmarkList, Catalogs } from "@/lib/api";
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

type BenchmarkItem = BenchmarkList["items"][number];

type Props = {
  items: BenchmarkItem[];
  catalogs: Catalogs;
  onCategoryChange: (instrumentId: number, category: string) => void | Promise<void>;
  onBenchmarkChange: (instrumentId: number, benchmark: string) => void | Promise<void>;
  busy: boolean;
};

export function BenchmarkOverridesTable({
  items,
  catalogs,
  onCategoryChange,
  onBenchmarkChange,
  busy,
}: Props) {
  return (
    <Card>
      <CardHeader className="p-5 pb-0">
        <CardTitle>Compare each holding to which index?</CardTitle>
      </CardHeader>
      <CardContent className="p-5 pt-4">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Holding</TableHead>
              <TableHead>Kind</TableHead>
              <TableHead>Fund category</TableHead>
              <TableHead>Compare to index</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((item) => (
              <TableRow
                key={item.instrument_id}
                data-needs-category={item.needs_category || undefined}
                className={
                  item.needs_category
                    ? "bg-warn/10 [&>td]:border-y [&>td]:border-warn/50"
                    : undefined
                }
              >
                <TableCell>{item.symbol}</TableCell>
                <TableCell>{item.instrument_type}</TableCell>
                <TableCell>
                  {item.instrument_type === "mf" ? (
                    <select
                      aria-label={`${item.symbol} fund category`}
                      value={item.mf_category ?? ""}
                      disabled={busy}
                      onChange={(event) =>
                        void onCategoryChange(item.instrument_id, event.target.value)
                      }
                    >
                      {item.needs_category ? (
                        <option value="" disabled>
                          Choose category
                        </option>
                      ) : null}
                      {catalogs.mf_categories.map((category) => (
                        <option key={category} value={category}>
                          {category}
                        </option>
                      ))}
                    </select>
                  ) : (
                    "—"
                  )}
                </TableCell>
                <TableCell>
                  <select
                    aria-label={`${item.symbol} comparison index`}
                    value={item.benchmark_index}
                    disabled={busy}
                    onChange={(event) =>
                      void onBenchmarkChange(item.instrument_id, event.target.value)
                    }
                  >
                    {catalogs.benchmark_indexes.map((index) => (
                      <option key={index} value={index}>
                        {index}
                      </option>
                    ))}
                  </select>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
