"use client";

import { useState } from "react";

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
    <section className="status-banner" data-kind="gap">
      <div>
        <strong>{message}</strong>
        <p>Export that range from Console, then upload the tradebook CSV here.</p>
      </div>
      <div className="control-row">
        <label className="field">
          <span>From</span>
          <input
            type="date"
            value={from}
            onChange={(event) => setFrom(event.target.value)}
          />
        </label>
        <label className="field">
          <span>To</span>
          <input
            type="date"
            value={to}
            onChange={(event) => setTo(event.target.value)}
          />
        </label>
      </div>
    </section>
  );
}
