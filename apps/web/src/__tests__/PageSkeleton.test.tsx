import { render, screen } from "@testing-library/react";
import { PageSkeleton } from "@/components/PageSkeleton";

it("renders overview skeleton with page-skeleton test id", () => {
  render(<PageSkeleton variant="overview" />);
  expect(screen.getByTestId("page-skeleton")).toBeInTheDocument();
});

it("renders settings auth and benchmarks test ids", () => {
  const { rerender } = render(<PageSkeleton variant="settings-auth" />);
  expect(screen.getByTestId("settings-auth-skeleton")).toBeInTheDocument();
  rerender(<PageSkeleton variant="settings-benchmarks" />);
  expect(
    screen.getByTestId("settings-benchmarks-skeleton"),
  ).toBeInTheDocument();
});
