"use client";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

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
    <Card>
      <CardHeader className="p-5 pb-0">
        <CardTitle>Your Zerodha account</CardTitle>
        <CardDescription>{status}</CardDescription>
      </CardHeader>
      <CardContent className="p-5 pt-4">
        <div className="control-row">
          <Button
            type="button"
            disabled={busy || !credentialsConfigured}
            onClick={() => void onLogin()}
          >
            {connected ? "Log in again" : "Log in with Zerodha"}
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={busy || !connected}
            onClick={() => void onRefresh()}
          >
            {connected ? "Refresh holdings" : "Refresh holdings (log in first)"}
          </Button>
        </div>
        <p className="mt-4 text-sm text-muted-foreground">
          Refresh holdings = sync holdings, append today’s trades, refresh
          prices. Missing history days → Import.
        </p>
      </CardContent>
    </Card>
  );
}
