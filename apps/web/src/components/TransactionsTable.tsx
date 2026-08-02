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
import type { HoldingTransactions } from "@/lib/api";
import { formatInr, formatPrice } from "@/lib/format";

type Transaction = HoldingTransactions["transactions"][number];

const SOURCE_LABELS: Record<string, string> = {
  csv: "CSV",
  api: "API",
};

function formatSource(source: string): string {
  return SOURCE_LABELS[source] ?? source;
}

type Props = {
  rows: Transaction[];
};

export function TransactionsTable({ rows }: Props) {
  return (
    <DataTableCard title="Transactions">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Date</TableHead>
            <TableHead>Side</TableHead>
            <TableHead>Qty</TableHead>
            <TableHead>Price</TableHead>
            <TableHead>Amount</TableHead>
            <TableHead>Source</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.length === 0 ? (
            <EmptyTableRow colSpan={6} />
          ) : (
            rows.map((row) => (
              <TableRow key={row.id}>
                <TableCell>{row.trade_date}</TableCell>
                <TableCell>{row.side}</TableCell>
                <TableCell>{row.quantity}</TableCell>
                <FormattedTableCell value={formatPrice(row.price)} />
                <FormattedTableCell value={formatInr(row.amount)} />
                <TableCell>{formatSource(row.source)}</TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </DataTableCard>
  );
}
