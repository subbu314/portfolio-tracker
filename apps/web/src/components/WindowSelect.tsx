"use client";

import { WINDOW_KEYS, type WindowKey } from "@/lib/windows";

type Props = {
  value: WindowKey;
  onChange: (w: WindowKey) => void;
  id?: string;
  ariaLabel?: string;
};

export function WindowSelect({
  value,
  onChange,
  id = "window",
  ariaLabel = "Window",
}: Props) {
  return (
    <label className="field">
      <span>Window</span>
      <select
        id={id}
        aria-label={ariaLabel}
        value={value}
        onChange={(e) => onChange(e.target.value as WindowKey)}
      >
        {WINDOW_KEYS.map((k) => (
          <option key={k} value={k}>
            {k}
          </option>
        ))}
      </select>
    </label>
  );
}
