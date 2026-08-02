"use client";

import Link from "next/link";
import type { StatusBannerModel } from "@/lib/status";

type Props = {
  model: StatusBannerModel | null;
  onRefresh: () => void | Promise<void>;
  refreshing?: boolean;
};

export function StatusBanner({ model, onRefresh, refreshing }: Props) {
  if (!model) return null;
  return (
    <div className="status-banner" data-kind={model.kind} role="status">
      <p>{model.message}</p>
      {model.ctaAction === "refresh" ? (
        <button
          type="button"
          disabled={model.disabled || refreshing}
          onClick={() => void onRefresh()}
        >
          {refreshing ? "Refreshing…" : model.ctaLabel}
        </button>
      ) : model.ctaHref ? (
        <Link href={model.ctaHref}>{model.ctaLabel}</Link>
      ) : null}
    </div>
  );
}
