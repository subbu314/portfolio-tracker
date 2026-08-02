import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { STORAGE_KEY } from "@/mocks/scenarios";

const reload = vi.fn();

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
  Object.defineProperty(window, "location", {
    configurable: true,
    value: { ...window.location, reload },
  });
  reload.mockReset();
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

it("writes scenario and reloads", async () => {
  const user = userEvent.setup();
  vi.stubEnv("NEXT_PUBLIC_USE_MOCKS", "true");
  const { ScenarioSwitcher } = await import("@/components/dev/ScenarioSwitcher");
  render(<ScenarioSwitcher />);

  await user.click(screen.getByRole("button", { name: /mock:/i }));
  await user.click(screen.getByRole("menuitem", { name: /gap/i }));

  expect(localStorage.getItem(STORAGE_KEY)).toBe("gap");
  expect(reload).toHaveBeenCalled();
});

it("seeds last-import report when picking import_errors", async () => {
  const user = userEvent.setup();
  vi.stubEnv("NEXT_PUBLIC_USE_MOCKS", "true");
  const { ScenarioSwitcher } = await import("@/components/dev/ScenarioSwitcher");
  render(<ScenarioSwitcher />);

  await user.click(screen.getByRole("button", { name: /mock:/i }));
  await user.click(screen.getByRole("menuitem", { name: /import errors/i }));

  const raw = sessionStorage.getItem("portfolio-tracker:last-import");
  expect(raw).toBeTruthy();
  expect(JSON.parse(raw!).format).toBe("console_tradebook");
  expect(JSON.parse(raw!).flagged_rows.length).toBeGreaterThan(0);
});

it("is hidden when mocks are disabled", async () => {
  vi.stubEnv("NEXT_PUBLIC_USE_MOCKS", "false");
  const { ScenarioSwitcher } = await import("@/components/dev/ScenarioSwitcher");
  render(<ScenarioSwitcher />);

  expect(screen.queryByRole("button", { name: /mock:/i })).not.toBeInTheDocument();
});
