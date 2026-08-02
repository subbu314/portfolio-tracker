"use client";

import { useState } from "react";

export function useBusyAction(fallbackMessage = "Action failed"): {
  busy: boolean;
  error: string | null;
  setError: (value: string | null) => void;
  run: (action: () => Promise<void>) => Promise<void>;
} {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<void>): Promise<void> {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (actionError) {
      setError(
        actionError instanceof Error ? actionError.message : fallbackMessage,
      );
    } finally {
      setBusy(false);
    }
  }

  return { busy, error, setError, run };
}
