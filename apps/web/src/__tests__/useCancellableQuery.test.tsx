import { act, renderHook, waitFor } from "@testing-library/react";
import { useCancellableQuery } from "@/hooks/useCancellableQuery";

it("ignores superseded responses", async () => {
  let resolveFirst!: (value: string) => void;
  const first = new Promise<string>((resolve) => {
    resolveFirst = resolve;
  });
  const queryFn = vi
    .fn()
    .mockImplementationOnce(() => first)
    .mockResolvedValueOnce("second");

  const { result, rerender } = renderHook(
    ({ key }) =>
      useCancellableQuery({
        key: [key],
        queryFn,
      }),
    { initialProps: { key: "a" } },
  );

  rerender({ key: "b" });
  await waitFor(() => expect(result.current.data).toBe("second"));

  await act(async () => {
    resolveFirst("first");
  });

  expect(result.current.data).toBe("second");
});

it("skips fetch when disabled", async () => {
  const queryFn = vi.fn().mockResolvedValue("x");
  const { result } = renderHook(() =>
    useCancellableQuery({
      key: ["k"],
      enabled: false,
      queryFn,
    }),
  );
  expect(queryFn).not.toHaveBeenCalled();
  expect(result.current.data).toBeNull();
  expect(result.current.error).toBeNull();
});
