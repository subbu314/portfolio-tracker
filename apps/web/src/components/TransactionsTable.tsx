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

export function TransactionsTable({ rows }: Props) {
  return (
    <Card>
      <CardHeader className="p-5 pb-0">
        <CardTitle>Transactions</CardTitle>
      </CardHeader>
      <CardContent className="p-5 pt-4">
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
              <TableRow>
                <TableCell
                  className="py-8 text-center text-muted-foreground"
                  colSpan={6}
                >
                  No rows
                </TableCell>
              </TableRow>
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
      </CardContent>
    </Card>
  );
}
