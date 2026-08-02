import { render, screen } from "@testing-library/react";
import { HoldingsPage } from "@/components/HoldingsPage";

const mocks = vi.hoisted(() => ({
  getHoldings: vi.fn(),
}));

vi.mock("@/lib/api", () => ({ api: mocks }));

beforeEach(() => {
  vi.clearAllMocks();
});

it("shows empty state when there are no holdings", async () => {
  mocks.getHoldings.mockResolvedValue([]);

  render(<HoldingsPage />);

  expect(await screen.findByTestId("empty-state")).toBeInTheDocument();
  expect(screen.getByText(/no holdings/i)).toBeInTheDocument();
});

it("shows skeleton while holdings load", () => {
  mocks.getHoldings.mockReturnValue(new Promise(() => {}));

  render(<HoldingsPage />);

  expect(screen.getByTestId("page-skeleton")).toBeInTheDocument();
  expect(screen.queryByText("Loading…")).not.toBeInTheDocument();
});
