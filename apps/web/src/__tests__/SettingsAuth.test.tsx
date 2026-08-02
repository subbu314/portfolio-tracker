import { render, screen } from "@testing-library/react";
import { SettingsAuthPanel } from "@/components/SettingsAuthPanel";
import { SettingsPage } from "@/components/SettingsPage";

const mocks = vi.hoisted(() => ({
  getAuthStatus: vi.fn(),
  getBenchmarkSettings: vi.fn(),
  getCatalogs: vi.fn(),
  getLoginUrl: vi.fn(),
  postSync: vi.fn(),
  putCategory: vi.fn(),
  putBenchmark: vi.fn(),
}));

vi.mock("@/lib/api", () => ({ api: mocks }));

describe("SettingsAuthPanel", () => {
  it("disables refresh when not logged in", () => {
    render(
      <SettingsAuthPanel
        connected={false}
        credentialsConfigured={true}
        lastSyncAt={null}
        onLogin={vi.fn()}
        onRefresh={vi.fn()}
        busy={false}
      />,
    );
    expect(screen.getByRole("button", { name: /log in with zerodha/i })).toBeEnabled();
    expect(
      screen.getByRole("button", { name: /refresh holdings \(log in first\)/i }),
    ).toBeDisabled();
  });

  it("enables refresh when logged in", () => {
    render(
      <SettingsAuthPanel
        connected={true}
        credentialsConfigured={true}
        lastSyncAt="2026-08-02T09:00:00+05:30"
        onLogin={vi.fn()}
        onRefresh={vi.fn()}
        busy={false}
      />,
    );
    expect(screen.getByRole("button", { name: /^refresh holdings$/i })).toBeEnabled();
    expect(screen.getByRole("button", { name: /log in again/i })).toBeEnabled();
  });
});

describe("SettingsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getAuthStatus.mockResolvedValue({
      connected: false,
      credentials_configured: false,
      last_sync_at: null,
    });
    mocks.getBenchmarkSettings.mockResolvedValue({ items: [] });
    mocks.getCatalogs.mockResolvedValue({
      mf_categories: [],
      benchmark_indexes: [],
    });
  });

  it("shows env secrets guidance as an alert, not a password field", async () => {
    render(<SettingsPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /api_key|api_secret|\.env/i,
    );
    expect(screen.queryByLabelText(/api_secret/i)).not.toBeInTheDocument();
  });
});
