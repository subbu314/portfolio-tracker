import { render, screen } from "@testing-library/react";
import { AllocationChart } from "@/components/AllocationChart";

describe("AllocationChart", () => {
  it("shows prices-missing copy when holdings exist but slices are empty", () => {
    render(<AllocationChart slices={[]} holdingsCount={3} />);
    expect(
      screen.getByText(/Allocation unavailable — prices missing/i),
    ).toBeInTheDocument();
  });

  it("shows no-holdings copy when portfolio is empty", () => {
    render(<AllocationChart slices={[]} holdingsCount={0} />);
    expect(screen.getByText(/No holdings yet/i)).toBeInTheDocument();
  });
});
