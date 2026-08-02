"use client";

import { useCallback, useEffect, useState } from "react";
import { BenchmarkOverridesTable } from "@/components/BenchmarkOverridesTable";
import { PageAlert } from "@/components/PageAlert";
import { SettingsAuthPanel } from "@/components/SettingsAuthPanel";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { useBusyAction } from "@/hooks/useBusyAction";
import {
  api,
  type AuthStatus,
  type BenchmarkList,
  type Catalogs,
} from "@/lib/api";

export function SettingsPage() {
  const [auth, setAuth] = useState<AuthStatus | null>(null);
  const [benchmarks, setBenchmarks] = useState<BenchmarkList | null>(null);
  const [catalogs, setCatalogs] = useState<Catalogs | null>(null);
  const { busy, error, setError, run } = useBusyAction();

  const loadSettings = useCallback(async () => {
    const [nextAuth, nextBenchmarks, nextCatalogs] = await Promise.all([
      api.getAuthStatus(),
      api.getBenchmarkSettings(),
      api.getCatalogs(),
    ]);
    setAuth(nextAuth);
    setBenchmarks(nextBenchmarks);
    setCatalogs(nextCatalogs);
  }, []);

  useEffect(() => {
    void loadSettings().catch((loadError: Error) => setError(loadError.message));
  }, [loadSettings, setError]);

  function onLogin() {
    return run(async () => {
      const { login_url } = await api.getLoginUrl();
      window.location.href = login_url;
    });
  }

  function onRefresh() {
    return run(async () => {
      await api.postSync();
      await loadSettings();
    });
  }

  function onCategoryChange(instrumentId: number, category: string) {
    return run(async () => {
      await api.putCategory(instrumentId, category);
      setBenchmarks(await api.getBenchmarkSettings());
    });
  }

  function onBenchmarkChange(instrumentId: number, benchmark: string) {
    return run(async () => {
      await api.putBenchmark(instrumentId, benchmark);
      setBenchmarks(await api.getBenchmarkSettings());
    });
  }

  return (
    <div className="stack">
      <h1>Settings</h1>
      <Alert className="border-border bg-surface-elevated text-muted-foreground">
        <AlertDescription>
          Kite api_key / api_secret live in <code>.env</code> (see{" "}
          <code>.env.example</code>); never entered here. Kite console redirect
          must match <code>KITE_REDIRECT_URL</code>.
        </AlertDescription>
      </Alert>
      {error ? <PageAlert>{error}</PageAlert> : null}
      {auth && !auth.credentials_configured ? (
        <div className="status-banner" data-kind="outdated" role="status">
          Set KITE_API_KEY and KITE_API_SECRET in .env before logging in.
        </div>
      ) : null}
      {auth ? (
        <SettingsAuthPanel
          connected={auth.connected}
          credentialsConfigured={auth.credentials_configured}
          lastSyncAt={auth.last_sync_at}
          onLogin={onLogin}
          onRefresh={onRefresh}
          busy={busy}
        />
      ) : (
        <div className="stack" data-testid="settings-auth-skeleton">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-20 w-full" />
        </div>
      )}
      {benchmarks && catalogs ? (
        <BenchmarkOverridesTable
          items={benchmarks.items}
          catalogs={catalogs}
          onCategoryChange={onCategoryChange}
          onBenchmarkChange={onBenchmarkChange}
          busy={busy}
        />
      ) : (
        <Skeleton
          className="h-64 w-full"
          data-testid="settings-benchmarks-skeleton"
        />
      )}
    </div>
  );
}
