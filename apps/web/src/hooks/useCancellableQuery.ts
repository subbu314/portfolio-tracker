"use client";

import { useEffect, useState } from "react";

type Options<T> = {
  key: readonly unknown[];
  enabled?: boolean;
  queryFn: () => Promise<T>;
};

export function useCancellableQuery<T>({
  key,
  enabled = true,
  queryFn,
}: Options<T>): {
  data: T | null;
  error: string | null;
  loading: boolean;
} {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const keyId = JSON.stringify(key);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setError(null);

    if (!enabled) {
      return () => {
        cancelled = true;
      };
    }

    void queryFn()
      .then((next) => {
        if (!cancelled) setData(next);
      })
      .catch((loadError: unknown) => {
        if (!cancelled) {
          setError(
            loadError instanceof Error ? loadError.message : "Request failed",
          );
        }
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- keyId/enabled are the cache identity; queryFn is recreated by callers
  }, [keyId, enabled]);

  return {
    data,
    error,
    loading: enabled && data === null && error === null,
  };
}
