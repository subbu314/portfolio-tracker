import { render, screen } from "@testing-library/react";
import { SettingsAuthPanel } from "@/components/SettingsAuthPanel";

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
