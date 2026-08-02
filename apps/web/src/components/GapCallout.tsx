"use client";

import { useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

type Props = {
  suggestedFrom: string;
  suggestedTo: string;
  message: string;
};

export function GapCallout({
  suggestedFrom,
  suggestedTo,
  message,
}: Props) {
  const [from, setFrom] = useState(suggestedFrom);
  const [to, setTo] = useState(suggestedTo);

  return (
    <Alert className="border-warn/55 bg-warn/10" data-kind="gap">
      <div>
        <AlertTitle>{message}</AlertTitle>
        <p>Export that range from Console, then upload the tradebook CSV here.</p>
      </div>
      <AlertDescription className="control-row">
        <label className="field">
          <span className="font-medium text-foreground">From</span>
          <input
            type="date"
            value={from}
            onChange={(event) => setFrom(event.target.value)}
          />
        </label>
        <label className="field">
          <span className="font-medium text-foreground">To</span>
          <input
            type="date"
            value={to}
            onChange={(event) => setTo(event.target.value)}
          />
        </label>
      </AlertDescription>
    </Alert>
  );
}
