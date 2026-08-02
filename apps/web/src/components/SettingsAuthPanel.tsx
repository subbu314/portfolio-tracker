"use client";

type Props = {
  connected: boolean;
  credentialsConfigured: boolean;
  lastSyncAt: string | null;
  onLogin: () => void | Promise<void>;
  onRefresh: () => void | Promise<void>;
  busy: boolean;
};

function formatLastSync(lastSyncAt: string | null) {
  if (!lastSyncAt) return "not yet";
  return new Date(lastSyncAt).toLocaleString();
}

export function SettingsAuthPanel({
  connected,
  credentialsConfigured,
  lastSyncAt,
  onLogin,
  onRefresh,
  busy,
}: Props) {
  const status = connected
    ? `Logged in · holdings last refreshed ${formatLastSync(lastSyncAt)}`
    : "Not logged in — log in once so we can load your holdings";

  return (
    <section className="panel">
      <h2>Your Zerodha account</h2>
      <p>{status}</p>
      <div className="control-row">
        <button
          type="button"
          disabled={busy || !credentialsConfigured}
          onClick={() => void onLogin()}
        >
          {connected ? "Log in again" : "Log in with Zerodha"}
        </button>
        <button
          type="button"
          disabled={busy || !connected}
          onClick={() => void onRefresh()}
        >
          {connected ? "Refresh holdings" : "Refresh holdings (log in first)"}
        </button>
      </div>
      <p className="muted">
        Refresh holdings = sync holdings, append today’s trades, refresh prices.
        Missing history days → Import.
      </p>
    </section>
  );
}
