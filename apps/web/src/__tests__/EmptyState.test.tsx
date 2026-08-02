import { render, screen } from "@testing-library/react";
import { EmptyState } from "@/components/EmptyState";
import { PageAlert } from "@/components/PageAlert";

it("renders empty panel copy and CTA link", () => {
  render(
    <EmptyState
      title="No holdings yet"
      description="Refresh after logging in with Zerodha."
      action={{ label: "Open Settings", href: "/settings" }}
    />,
  );
  expect(screen.getByText("No holdings yet")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /open settings/i })).toHaveAttribute(
    "href",
    "/settings",
  );
});

it("renders page errors via Alert", () => {
  render(<PageAlert>Network failed</PageAlert>);
  expect(screen.getByRole("alert")).toHaveTextContent("Network failed");
});
