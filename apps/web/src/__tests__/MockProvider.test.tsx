import { render, screen, waitFor } from "@testing-library/react";

const browserMock = vi.hoisted(() => ({
  load: vi.fn(),
  start: vi.fn(),
}));

vi.mock("@/mocks/browser", () => {
  browserMock.load();
  return { worker: { start: browserMock.start } };
});

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}));

beforeEach(() => {
  browserMock.load.mockReset();
  browserMock.start.mockReset();
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

it("mocksEnabled is false in production even when USE_MOCKS is true", async () => {
  vi.stubEnv("NEXT_PUBLIC_USE_MOCKS", "true");
  vi.stubEnv("NODE_ENV", "production");
  const { mocksEnabled } = await import("@/lib/mocks-enabled");

  expect(mocksEnabled()).toBe(false);
});

async function loadMockProvider(useMocks: boolean) {
  vi.stubEnv("NEXT_PUBLIC_USE_MOCKS", String(useMocks));
  return import("@/components/dev/MockProvider");
}

it("does not import or start the worker when mocks are disabled", async () => {
  const { MockProvider } = await loadMockProvider(false);
  render(
    <MockProvider>
      <p>child</p>
    </MockProvider>,
  );

  expect(screen.getByText("child")).toBeInTheDocument();
  expect(browserMock.load).not.toHaveBeenCalled();
  expect(browserMock.start).not.toHaveBeenCalled();
});

it("starts the worker when mocks are enabled", async () => {
  browserMock.start.mockResolvedValue(undefined);
  const { MockProvider } = await loadMockProvider(true);
  render(
    <MockProvider>
      <p>child</p>
    </MockProvider>,
  );

  await waitFor(() => expect(browserMock.start).toHaveBeenCalledOnce());
  expect(browserMock.start).toHaveBeenCalledWith({
    onUnhandledRequest: "warn",
    serviceWorker: { url: "/mockServiceWorker.js" },
  });
  expect(screen.getByText("child")).toBeInTheDocument();
});

it("does not render children when worker startup fails", async () => {
  browserMock.start.mockRejectedValueOnce(new Error("worker failed"));
  const { MockProvider } = await loadMockProvider(true);
  render(
    <MockProvider>
      <p>child</p>
    </MockProvider>,
  );

  expect(await screen.findByRole("alert")).toHaveTextContent(/could not start/i);
  expect(screen.queryByText("child")).not.toBeInTheDocument();
});

it("renders the same mock composition as the root layout", async () => {
  browserMock.start.mockResolvedValue(undefined);
  vi.stubEnv("NEXT_PUBLIC_USE_MOCKS", "true");
  const [{ MockProvider }, { AppShell }, { ScenarioSwitcher }] = await Promise.all([
    import("@/components/dev/MockProvider"),
    import("@/components/AppShell"),
    import("@/components/dev/ScenarioSwitcher"),
  ]);

  render(
    <MockProvider>
      <AppShell>
        <p>page content</p>
      </AppShell>
      <ScenarioSwitcher />
    </MockProvider>,
  );

  await waitFor(() => expect(browserMock.start).toHaveBeenCalledOnce());
  expect(screen.getByTestId("app-shell")).toBeInTheDocument();
  expect(screen.getByText("page content")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /mock: happy/i })).toBeInTheDocument();
});
