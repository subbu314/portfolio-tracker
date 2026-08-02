import { render, screen, within } from "@testing-library/react";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, expect, it } from "vitest";
import { OverviewPage } from "@/components/OverviewPage";
import { handlers } from "@/mocks/handlers";
import { STORAGE_KEY } from "@/mocks/scenarios";

const server = setupServer(...handlers);

beforeAll(() => server.listen());
afterEach(() => {
  server.resetHandlers();
  localStorage.clear();
});
afterAll(() => server.close());

it("shows skeleton before MSW core responses resolve", () => {
  render(<OverviewPage />);

  expect(screen.getByTestId("page-skeleton")).toBeInTheDocument();
});

it("shows empty allocation state when no holdings exist", async () => {
  localStorage.setItem(STORAGE_KEY, "empty");

  render(<OverviewPage />);

  expect(await screen.findByText("No holdings yet")).toBeInTheDocument();
  const returnCard = screen
    .getByRole("heading", { name: "Portfolio return" })
    .closest(".metric-card");
  const outperformanceCard = screen
    .getByRole("heading", { name: "Outperformance" })
    .closest(".metric-card");

  expect(returnCard).not.toBeNull();
  expect(outperformanceCard).not.toBeNull();
  expect(within(returnCard!).getByText("N/A")).toBeInTheDocument();
  expect(within(outperformanceCard!).getByText("N/A")).toBeInTheDocument();
  expect(screen.queryByText("15.00%")).not.toBeInTheDocument();
  expect(
    within(outperformanceCard!).queryByText(/you beat category benchmarks/i),
  ).not.toBeInTheDocument();
});

it("shows negative returns and trailing outperformance copy", async () => {
  localStorage.setItem(STORAGE_KEY, "negative");

  render(<OverviewPage />);

  const returnCard = (
    await screen.findByRole("heading", { name: "Portfolio return" })
  ).closest(".metric-card");
  const outperformanceCard = screen
    .getByRole("heading", { name: "Outperformance" })
    .closest(".metric-card");

  expect(returnCard).not.toBeNull();
  expect(outperformanceCard).not.toBeNull();
  expect(within(returnCard!).getByText("-12.00%")).toBeInTheDocument();
  expect(within(outperformanceCard!).getByText("-2.50 pp")).toBeInTheDocument();
  expect(
    within(outperformanceCard!).getByText(
      "You trail category benchmarks by 2.50 pp",
    ),
  ).toBeInTheDocument();
  expect(screen.queryByText("15.00%")).not.toBeInTheDocument();
  expect(
    within(outperformanceCard!).queryByText(/you beat category benchmarks/i),
  ).not.toBeInTheDocument();
});

it("shows login banner when logged_out", async () => {
  localStorage.setItem(STORAGE_KEY, "logged_out");

  render(<OverviewPage />);

  expect(await screen.findByText(/not logged in/i)).toBeInTheDocument();
});

it("shows outdated banner when stale", async () => {
  localStorage.setItem(STORAGE_KEY, "stale");

  render(<OverviewPage />);

  expect(await screen.findByText(/outdated/i)).toBeInTheDocument();
});

it("shows gap banner when gap", async () => {
  localStorage.setItem(STORAGE_KEY, "gap");

  render(<OverviewPage />);

  expect(await screen.findByRole("status")).toHaveTextContent(/incomplete/i);
});
