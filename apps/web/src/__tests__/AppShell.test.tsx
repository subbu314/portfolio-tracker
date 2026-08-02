import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AppShell } from "@/components/AppShell";

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}));

describe("AppShell", () => {
  beforeEach(() => {
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
      onchange: null,
    }));
  });

  it("renders brand and five nav items", () => {
    render(
      <AppShell>
        <p>child</p>
      </AppShell>,
    );
    expect(screen.getByText("Portfolio Tracker")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /overview/i })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: /holdings/i })).toHaveAttribute("href", "/holdings");
    expect(screen.getByRole("link", { name: /import/i })).toHaveAttribute("href", "/import");
    expect(screen.getByRole("link", { name: /settings/i })).toHaveAttribute("href", "/settings");
    expect(screen.getByRole("link", { name: /glossary/i })).toHaveAttribute("href", "/glossary");
    expect(screen.getByText("child")).toBeInTheDocument();
  });

  it("collapses nav to data-collapsed", async () => {
    const user = userEvent.setup();
    render(
      <AppShell>
        <p>child</p>
      </AppShell>,
    );
    const toggle = screen.getByRole("button", { name: /collapse|expand/i });
    await user.click(toggle);
    expect(screen.getByTestId("app-shell")).toHaveAttribute("data-collapsed", "true");
  });

  it("keeps nav link accessible names when collapsed", async () => {
    const user = userEvent.setup();
    render(
      <AppShell>
        <p>child</p>
      </AppShell>,
    );
    await user.click(screen.getByRole("button", { name: /collapse navigation/i }));
    expect(screen.getByRole("link", { name: /overview/i })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: /holdings/i })).toHaveAttribute("href", "/holdings");
    expect(screen.getByRole("link", { name: /import/i })).toHaveAttribute("href", "/import");
    expect(screen.getByRole("link", { name: /settings/i })).toHaveAttribute("href", "/settings");
    expect(screen.getByRole("link", { name: /glossary/i })).toHaveAttribute("href", "/glossary");
  });

  it("uses lucide icons instead of unicode placeholders", () => {
    render(
      <AppShell>
        <p>child</p>
      </AppShell>,
    );

    const overview = screen.getByRole("link", { name: /overview/i });
    expect(overview.querySelector("svg")).not.toBeNull();
    expect(overview.textContent).not.toMatch(/◉/);
  });

  it("does not render scenario switcher when mocks are disabled", () => {
    render(
      <AppShell>
        <p>child</p>
      </AppShell>,
    );

    expect(screen.queryByRole("button", { name: /mock:/i })).not.toBeInTheDocument();
  });

  it("defaults to collapsed below 760px", () => {
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: query.includes("760"),
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
      onchange: null,
    }));
    render(
      <AppShell>
        <p>child</p>
      </AppShell>,
    );
    expect(screen.getByTestId("app-shell")).toHaveAttribute(
      "data-collapsed",
      "true",
    );
  });
});
