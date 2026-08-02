export type StatusBannerModel = {
  kind: "login" | "gap" | "outdated" | "incomplete";
  message: string;
  ctaLabel: string;
  ctaHref?: string;
  ctaAction?: "refresh";
  disabled?: boolean;
};

export type StatusInput = {
  connected: boolean;
  lastSyncAt: string | null;
  incomplete: boolean;
  gap: { suggested_from: string; suggested_to: string; message: string } | null;
  today: string; // YYYY-MM-DD in Asia/Kolkata
};

function syncDay(iso: string | null): string | null {
  if (!iso) return null;
  // Prefer calendar day in IST for "refreshed today"
  try {
    return new Intl.DateTimeFormat("en-CA", {
      timeZone: "Asia/Kolkata",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso.slice(0, 10);
  }
}

export function deriveStatusBanner(input: StatusInput): StatusBannerModel | null {
  if (!input.connected) {
    return {
      kind: "login",
      message: "Not logged in — log in once so we can load your holdings",
      ctaLabel: "Log in with Zerodha",
      ctaHref: "/settings",
    };
  }
  if (input.gap) {
    return {
      kind: "gap",
      message: input.gap.message || "Trade history looks incomplete",
      ctaLabel: "Open Import",
      ctaHref: "/import",
    };
  }
  const day = syncDay(input.lastSyncAt);
  const syncStale = !day || day < input.today;
  if (syncStale) {
    return {
      kind: "outdated",
      message: "Holdings may be outdated",
      ctaLabel: "Refresh holdings",
      ctaAction: "refresh",
      disabled: !input.connected,
    };
  }
  if (input.incomplete) {
    return {
      kind: "incomplete",
      message: "Some prices or benchmarks are missing",
      ctaLabel: "View holdings",
      ctaHref: "/holdings",
    };
  }
  return null;
}

export function todayIst(): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Kolkata",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}
