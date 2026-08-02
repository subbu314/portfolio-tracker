"use client";

import { useEffect, useState, type ReactNode } from "react";

const useMocks = process.env.NEXT_PUBLIC_USE_MOCKS === "true";

export function MockProvider({ children }: { children: ReactNode }) {
  const [isReady, setIsReady] = useState(!useMocks);

  useEffect(() => {
    if (!useMocks) return;

    let cancelled = false;

    void import("@/mocks/browser").then(async ({ worker }) => {
      await worker.start({
        onUnhandledRequest: "bypass",
        serviceWorker: { url: "/mockServiceWorker.js" },
      });

      if (!cancelled) setIsReady(true);
    });

    return () => {
      cancelled = true;
    };
  }, []);

  if (!isReady) {
    return (
      <div className="grid min-h-screen place-items-center text-muted-foreground">
        Starting mocks…
      </div>
    );
  }

  return children;
}
