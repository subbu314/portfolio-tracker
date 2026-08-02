import { StrictMode } from "react";
import { render, waitFor } from "@testing-library/react";
import AuthCallbackPage from "@/app/auth/callback/page";

const mocks = vi.hoisted(() => ({
  postCallback: vi.fn(),
  replace: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  api: { postCallback: mocks.postCallback },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mocks.replace }),
  useSearchParams: () => new URLSearchParams("request_token=single-use-token"),
}));

beforeEach(() => {
  vi.clearAllMocks();
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
