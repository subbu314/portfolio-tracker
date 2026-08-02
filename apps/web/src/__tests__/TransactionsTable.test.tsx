import { render, screen } from "@testing-library/react";
import { TransactionsTable } from "@/components/TransactionsTable";

describe("TransactionsTable", () => {
  it("renders date side qty price amount source labels", () => {
    render(
      <TransactionsTable
        rows={[
          {
            id: 1,
            trade_date: "2024-01-10",
            side: "buy",
            quantity: 5,
            price: 2000,
            fees: 10,
            amount: 10000,
            source: "csv",
          },
        ]}
      />,
    );
    expect(screen.getByText("2024-01-10")).toBeInTheDocument();
    expect(screen.getByText("buy")).toBeInTheDocument();
    expect(screen.getByText("CSV")).toBeInTheDocument();
    expect(screen.getByText(/10,000/)).toBeInTheDocument();
  });
});
