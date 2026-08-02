import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { STORAGE_KEY } from "@/mocks/scenarios";

const reload = vi.fn();

beforeEach(() => {
  localStorage.clear();
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

it("is hidden when mocks are disabled", async () => {
  vi.stubEnv("NEXT_PUBLIC_USE_MOCKS", "false");
  const { ScenarioSwitcher } = await import("@/components/dev/ScenarioSwitcher");
  render(<ScenarioSwitcher />);

  expect(screen.queryByRole("button", { name: /mock:/i })).not.toBeInTheDocument();
});
