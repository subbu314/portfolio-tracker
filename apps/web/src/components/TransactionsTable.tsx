import type { HoldingTransactions } from "@/lib/api";
import { formatInr } from "@/lib/format";

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
    <section className="panel">
      <h2>Transactions</h2>
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Side</th>
            <th>Qty</th>
            <th>Price</th>
            <th>Amount</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              <td>{row.trade_date}</td>
              <td>{row.side}</td>
              <td>{row.quantity}</td>
              <td>{formatInr(row.price)}</td>
              <td>{formatInr(row.amount)}</td>
              <td>{formatSource(row.source)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
