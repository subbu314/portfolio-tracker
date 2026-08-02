"use client";

import Link from "next/link";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import type { StatusBannerModel } from "@/lib/status";
import { cn } from "@/lib/utils";

type Props = {
  model: StatusBannerModel | null;
  onRefresh: () => void | Promise<void>;
  refreshing?: boolean;
};

export function StatusBanner({ model, onRefresh, refreshing }: Props) {
  if (!model) return null;
  return (
    <Alert
      role="status"
      data-kind={model.kind}
      className={cn(
        model.kind === "outdated" ||
          model.kind === "gap" ||
          model.kind === "incomplete"
          ? "border-warn/55 bg-warn/10"
          : "bg-surface-elevated",
      )}
    >
      <AlertDescription className="flex flex-wrap items-center gap-3">
        <p className="m-0 flex-1">{model.message}</p>
        {model.ctaAction === "refresh" ? (
          <Button
            type="button"
            size="sm"
            disabled={model.disabled || refreshing}
            onClick={() => void onRefresh()}
          >
            {refreshing ? "Refreshing…" : model.ctaLabel}
          </Button>
        ) : model.ctaHref ? (
          <Button asChild size="sm" variant="link">
            <Link href={model.ctaHref}>{model.ctaLabel}</Link>
          </Button>
        ) : null}
      </AlertDescription>
    </Alert>
  );
}
