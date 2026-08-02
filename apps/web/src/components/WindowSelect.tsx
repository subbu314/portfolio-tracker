"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
    <div className="flex flex-col gap-1.5 text-sm">
      <span id={`${id}-label`} className="text-muted-foreground">
        Window
      </span>
      <Select
        value={value}
        onValueChange={(nextValue) => onChange(nextValue as WindowKey)}
      >
        <SelectTrigger
          id={id}
          aria-label={ariaLabel}
          className="min-w-[7rem]"
        >
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {WINDOW_KEYS.map((key) => (
            <SelectItem key={key} value={key}>
              {key}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
