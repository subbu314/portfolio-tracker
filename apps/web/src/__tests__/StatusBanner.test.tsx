import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StatusBanner } from "@/components/StatusBanner";

describe("StatusBanner", () => {
  it("disables refresh when model.disabled", () => {
    render(
      <StatusBanner
        model={{
          kind: "outdated",
          message: "Holdings may be outdated",
          ctaLabel: "Refresh holdings",
          ctaAction: "refresh",
          disabled: true,
        }}
        onRefresh={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: /refresh holdings/i })).toBeDisabled();
  });

  it("fires onRefresh for outdated CTA", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn();
    render(
      <StatusBanner
        model={{
          kind: "outdated",
          message: "Holdings may be outdated",
          ctaLabel: "Refresh holdings",
          ctaAction: "refresh",
        }}
        onRefresh={onRefresh}
      />,
    );
    await user.click(screen.getByRole("button", { name: /refresh holdings/i }));
    expect(onRefresh).toHaveBeenCalled();
  });

  it("renders link CTA for gap", () => {
    render(
      <StatusBanner
        model={{
          kind: "gap",
          message: "gap",
          ctaLabel: "Open Import",
          ctaHref: "/import",
        }}
        onRefresh={vi.fn()}
      />,
    );
    expect(screen.getByRole("link", { name: /open import/i })).toHaveAttribute(
      "href",
      "/import",
    );
  });
});
