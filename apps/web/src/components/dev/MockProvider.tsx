"use client";

import { mocksEnabled } from "@/lib/mocks-enabled";
import { useEffect, useState, type ReactNode } from "react";

const useMocks = mocksEnabled();

export function MockProvider({ children }: { children: ReactNode }) {
  const [isReady, setIsReady] = useState(!useMocks);
  const [startupError, setStartupError] = useState(false);

  useEffect(() => {
    if (!useMocks) return;

    let cancelled = false;

    void startWorker()
      .then(() => {
        if (!cancelled) setIsReady(true);
      })
      .catch(() => {
        if (!cancelled) setStartupError(true);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (startupError) {
    return (
      <>
        <div role="alert" className="p-4 text-sm text-destructive">
          Mock API could not start. Continuing without mocks.
        </div>
        {children}
      </>
    );
  }

  if (!isReady) {
    return (
      <div className="grid min-h-screen place-items-center text-muted-foreground">
        Starting mocks…
      </div>
    );
  }

  return children;
}

async function startWorker(): Promise<void> {
  const { worker } = await import("@/mocks/browser");
  await worker.start({
    onUnhandledRequest: "bypass",
    serviceWorker: { url: "/mockServiceWorker.js" },
  });
}
