import { act, renderHook } from "@testing-library/react";
import { useBusyAction } from "@/hooks/useBusyAction";

it("sets busy around the action and captures errors", async () => {
  const { result } = renderHook(() => useBusyAction("Action failed"));
  expect(result.current.busy).toBe(false);

  let release!: () => void;
  const pending = new Promise<void>((resolve) => {
    release = resolve;
  });

  let runPromise: Promise<void>;
  act(() => {
    runPromise = result.current.run(() => pending);
  });
  expect(result.current.busy).toBe(true);

  await act(async () => {
    release();
    await runPromise!;
  });
  expect(result.current.busy).toBe(false);
  expect(result.current.error).toBeNull();

  await act(async () => {
    await result.current.run(async () => {
      throw new Error("boom");
    });
  });
  expect(result.current.error).toBe("boom");
});
