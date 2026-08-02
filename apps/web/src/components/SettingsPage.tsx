"use client";

import { useCallback, useEffect, useState } from "react";
import { BenchmarkOverridesTable } from "@/components/BenchmarkOverridesTable";
import { SettingsAuthPanel } from "@/components/SettingsAuthPanel";
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
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

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
  }, [loadSettings]);

  async function runAction(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  function onLogin() {
    return runAction(async () => {
      const { login_url } = await api.getLoginUrl();
      window.location.href = login_url;
    });
  }

  function onRefresh() {
    return runAction(async () => {
      await api.postSync();
      setAuth(await api.getAuthStatus());
    });
  }

  function onCategoryChange(instrumentId: number, category: string) {
    return runAction(async () => {
      await api.putCategory(instrumentId, category);
      setBenchmarks(await api.getBenchmarkSettings());
    });
  }

  function onBenchmarkChange(instrumentId: number, benchmark: string) {
    return runAction(async () => {
      await api.putBenchmark(instrumentId, benchmark);
      setBenchmarks(await api.getBenchmarkSettings());
    });
  }

  return (
    <div className="stack">
      <h1>Settings</h1>
      <p>
        Kite api_key / api_secret live in <code>.env</code> (see{" "}
        <code>.env.example</code>); never entered here. Kite console redirect
        must match <code>KITE_REDIRECT_URL</code>.
      </p>
      {error ? <p role="alert">{error}</p> : null}
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
        <p>Loading account settings…</p>
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
        <p>Loading benchmark settings…</p>
      )}
    </div>
  );
}
