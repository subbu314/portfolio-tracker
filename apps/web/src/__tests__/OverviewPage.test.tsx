import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { OverviewPage } from "@/components/OverviewPage";

type Series = {
  available: boolean;
  points: {
    date: string;
    portfolio_return: number | null;
    benchmark_return: number | null;
  }[];
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((next) => {
    resolve = next;
  });
  return { promise, resolve };
}

const mocks = vi.hoisted(() => ({
  getOverview: vi.fn(),
  getHoldings: vi.fn(),
  getAuthStatus: vi.fn(),
  getAlerts: vi.fn(),
  getPortfolioSeries: vi.fn(),
  postSync: vi.fn(),
}));

vi.mock("@/lib/api", () => ({ api: mocks }));
vi.mock("@/components/AllocationChart", () => ({
  AllocationChart: () => null,
}));
vi.mock("@/components/MetricCard", () => ({ MetricCard: () => null }));
vi.mock("@/components/StatusBanner", () => ({ StatusBanner: () => null }));
vi.mock("@/components/ValueHero", () => ({ ValueHero: () => null }));
vi.mock("@/components/MetricWindowSelects", () => ({
  MetricWindowSelects: ({
    window,
    onWindowChange,
  }: {
    window: string;
    onWindowChange: (window: "ITD" | "1Y" | "3Y" | "5Y") => void;
  }) => (
    <select
      aria-label="Chart window"
      value={window}
      onChange={(event) =>
        onWindowChange(event.target.value as "ITD" | "1Y" | "3Y" | "5Y")
      }
    >
      <option value="ITD">ITD</option>
      <option value="1Y">1Y</option>
      <option value="3Y">3Y</option>
      <option value="5Y">5Y</option>
    </select>
  ),
}));
vi.mock("@/components/ReturnSeriesChart", () => ({
  ReturnSeriesChart: ({
    points,
  }: {
    points: { date: string }[];
  }) => <p>{points[0]?.date ?? "Empty series"}</p>,
}));

const series = (date: string): Series => ({
  available: true,
  points: [
    {
      date,
      portfolio_return: 0.1,
      benchmark_return: 0.05,
    },
  ],
});

beforeEach(() => {
  vi.clearAllMocks();
  mocks.getOverview.mockResolvedValue({
    total_value: 100,
    absolute: { invested_cost: 90, gain_inr: 10, gain_pct: 0.1 },
    windows: {},
    incomplete: false,
  });
  mocks.getHoldings.mockResolvedValue([]);
  mocks.getAuthStatus.mockResolvedValue({
    connected: true,
    last_sync_at: new Date().toISOString(),
  });
  mocks.getAlerts.mockResolvedValue({ gap: null });
});

it("clears previous series while a new window loads", async () => {
  const user = userEvent.setup();
  const itd = deferred<Series>();
  const oneYear = deferred<Series>();
  mocks.getPortfolioSeries.mockImplementation((window: string) =>
    window === "ITD" ? itd.promise : oneYear.promise,
  );

  render(<OverviewPage />);
  itd.resolve(series("2020-01-01"));
  expect(await screen.findByText("2020-01-01")).toBeInTheDocument();

  await user.selectOptions(screen.getByLabelText("Chart window"), "1Y");

  expect(screen.getByText("Empty series")).toBeInTheDocument();
  expect(screen.queryByText("2020-01-01")).not.toBeInTheDocument();
});

it("ignores a superseded window response", async () => {
  const user = userEvent.setup();
  const itd = deferred<Series>();
  const oneYear = deferred<Series>();
  mocks.getPortfolioSeries.mockImplementation((window: string) =>
    window === "ITD" ? itd.promise : oneYear.promise,
  );

  render(<OverviewPage />);
  await waitFor(() => expect(mocks.getPortfolioSeries).toHaveBeenCalledWith("ITD"));
  await user.selectOptions(screen.getByLabelText("Chart window"), "1Y");

  oneYear.resolve(series("2025-01-01"));
  expect(await screen.findByText("2025-01-01")).toBeInTheDocument();
  itd.resolve(series("2020-01-01"));

  await waitFor(() =>
    expect(screen.queryByText("2020-01-01")).not.toBeInTheDocument(),
  );
  expect(screen.getByText("2025-01-01")).toBeInTheDocument();
});
