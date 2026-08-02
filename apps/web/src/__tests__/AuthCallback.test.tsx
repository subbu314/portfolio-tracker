import { StrictMode } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import AuthCallbackPage from "@/app/auth/callback/page";

const mocks = vi.hoisted(() => ({
  postCallback: vi.fn(),
  replace: vi.fn(),
  searchParams: new URLSearchParams("request_token=single-use-token"),
}));

vi.mock("@/lib/api", () => ({
  api: { postCallback: mocks.postCallback },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mocks.replace }),
  useSearchParams: () => mocks.searchParams,
}));

beforeEach(() => {
  vi.clearAllMocks();
  mocks.searchParams = new URLSearchParams("request_token=single-use-token");
  mocks.postCallback.mockReturnValue(new Promise(() => {}));
});

it("exchanges a request token only once when Strict Mode replays effects", async () => {
  render(
    <StrictMode>
      <AuthCallbackPage />
    </StrictMode>,
  );

  await waitFor(() => expect(mocks.postCallback).toHaveBeenCalled());
  expect(mocks.postCallback).toHaveBeenCalledTimes(1);
  expect(mocks.postCallback).toHaveBeenCalledWith("single-use-token");
});

it("links to settings when callback exchange fails", async () => {
  mocks.postCallback.mockRejectedValue(new Error("exchange failed"));
  render(<AuthCallbackPage />);

  expect(await screen.findByRole("alert")).toHaveTextContent(/exchange failed/i);
  expect(screen.getByRole("link", { name: /settings/i })).toHaveAttribute(
    "href",
    "/settings",
  );
});

it("shows callback status errors without exchanging a token", async () => {
  mocks.searchParams = new URLSearchParams("status=error");
  render(<AuthCallbackPage />);

  expect(await screen.findByRole("alert")).toHaveTextContent(
    /cancelled or failed/i,
  );
  expect(mocks.postCallback).not.toHaveBeenCalled();
});
