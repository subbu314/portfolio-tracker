# Portfolio Tracker UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the dark Next.js analytics UI from `2026-08-02-portfolio-tracker-ui-design.md` — Overview, Holdings (+ detail), Import, Settings, Glossary — wired to the existing FastAPI client in `apps/web/src/lib/api.ts`.

**Architecture:** App Router pages under `apps/web/src/app` with a shared `AppShell` layout. Interactive Window/Metric controls and charts are client components; data loads via the handwritten `api` client (`NEXT_PUBLIC_API_URL`, `cache: "no-store"`). Metrics stay server-authoritative — UI only formats and selects windows. Chart series use absolute cumulative return only; XIRR/CAGR chart Metric shows N/A until a later API plan.

**Tech Stack:** Next.js 15, React 19, TypeScript, Recharts, Vitest + Testing Library (jsdom), existing `api.ts` / `api-types.ts` (do not hand-edit generated types).

## Global Constraints

- Do **not** rename API JSON fields (`ITD`, `1Y`, `3Y`, `5Y`; rates as fractions; excess as pp)
- Do **not** hand-edit `apps/web/src/lib/api-types.ts` or `apps/web/openapi.json`
- Prefer existing `api.*` methods; no new FastAPI endpoints in this plan
- Dark theme only; no light/system theme
- Kite secrets never in the browser — `.env` / `.env.example` only
- N/A windows/metrics render as `N/A`, never `0`
- Last import report: **browser sessionStorage** (API does not persist it)
- Stale holdings: derive from `auth/status.last_sync_at` + `overview.incomplete` / `alerts` — no dedicated stale flag
- Chart Metric Absolute → `GET /portfolio/series` or holding series; Metric XIRR/CAGR → empty chart + N/A copy (series API is absolute-only)
- Out of scope: Playwright e2e, churn UI, Performance nav item, light theme, entering api_key/api_secret in UI
- After each task: `cd apps/web && npm test` green; final task also `npm run build`
- Prefer edit over rewrite; YAGNI; TDD; frequent commits

## Prerequisite (already shipped)

UI API gaps plan (`2026-08-02-ui-api-gaps.md`) is implemented. Confirm before starting:

| Need | Endpoint / client |
| ---- | ----------------- |
| Overview scalars + windows | `api.getOverview()` → `GET /portfolio/overview` |
| Holdings list + `mf_category` | `api.getHoldings()` → `GET /portfolio/holdings` |
| Holding detail | `api.getHolding(id)` → `GET /portfolio/holdings/{id}` |
| Transactions | `api.getHoldingTransactions(id)` |
| Portfolio chart | `api.getPortfolioSeries(window)` → absolute only |
| Holding chart | `api.getHoldingSeries(id, window)` → absolute only |
| Alerts / gap | `api.getAlerts()` |
| Auth | `api.getAuthStatus`, `getLoginUrl`, `postCallback`, `postLogout` |
| Sync | `api.postSync()` |
| Import CSV | `api.postImportCsv(file)` |
| Benchmarks + catalogs | `api.getBenchmarkSettings`, `getCatalogs`, `putBenchmark`, `putCategory` |

Do **not** use `api.getPerformance()` for v1 UI (Performance folded into Overview).

## API → UI wiring map

| UI surface | Reads | Writes | Notes |
| ---------- | ----- | ------ | ----- |
| StatusBanner | `getAuthStatus`, `getAlerts`, `getOverview` (`incomplete`) | `postSync` | Gap → link `/import`; not logged in → `/settings` |
| ValueHero | `overview.total_value`, `overview.absolute.*` | — | ITD absolute story; ignore Window |
| Portfolio return card | `overview.windows[window].{xirr\|cagr\|absolute_pct}` | — | Default Metric XIRR; local Metric+Window |
| Outperformance card | `overview.windows[window].{xirr\|cagr\|absolute}_excess_pp` + `benchmark_return` | — | Label “Outperformance”; breakdown = portfolio % − bench % when both non-null |
| Overview chart | `getPortfolioSeries(window)` | — | Only when Metric=Absolute; else N/A |
| Allocation donut | **Holdings**, not `overview.allocation` | — | API allocation is per-symbol; aggregate by `instrument_type` client-side |
| Holdings tables | `getHoldings()` + page Window | — | Split `equity`+`etf` vs `mf`; columns from `holding.windows[window]` |
| Holding detail | `getHolding`, `getHoldingTransactions`, `getHoldingSeries` | — | Window local; no benchmark edit |
| Import | `getAlerts().gap`, `postImportCsv` | — | Report → `sessionStorage` |
| Settings auth | status + login-url + sync | OAuth via web callback page → `postCallback` | Update `.env.example` redirect to Next |
| Settings benchmarks | `getBenchmarkSettings` + `getCatalogs` | `putBenchmark` / `putCategory` | Dropdowns data-driven from catalogs |
| Glossary | static | — | No API |

**Rate / pp formatting (existing):** `formatPct` multiplies by 100; `formatPp` treats value as already-pp; `formatInr` for ₹.

**OAuth:** Prefer Kite redirect → Next.js `/auth/callback?request_token=…` → `api.postCallback` → `/settings`. Document `KITE_REDIRECT_URL=http://localhost:3000/auth/callback` in `.env.example` (API GET callback remains for live smoke).

## File Structure

```
apps/web/
  package.json                         # Task 1: recharts, testing-library, jsdom
  vitest.config.ts                     # Task 1: jsdom environment
  .env.example (repo root)             # Task 8: web OAuth redirect example
  src/
    app/
      globals.css                      # Task 1: dark theme tokens
      layout.tsx                       # Task 1: wrap AppShell
      page.tsx                         # Task 4: Overview (replace stub)
      holdings/
        page.tsx                       # Task 5
        [id]/page.tsx                   # Task 6
      import/page.tsx                  # Task 7
      settings/page.tsx                # Task 8
      glossary/page.tsx                # Task 9
      auth/callback/page.tsx           # Task 8
    components/
      AppShell.tsx                     # Task 1
      StatusBanner.tsx                 # Task 3
      WindowSelect.tsx                 # Task 3
      MetricWindowSelects.tsx          # Task 3
      ValueHero.tsx                    # Task 4
      MetricCard.tsx                   # Task 4
      AllocationChart.tsx              # Task 4
      ReturnSeriesChart.tsx            # Task 4
      HoldingsTable.tsx                # Task 5
      TransactionsTable.tsx            # Task 6
      CsvUpload.tsx                    # Task 7
      ImportReport.tsx                 # Task 7
      GapCallout.tsx                   # Task 7
      BenchmarkOverridesTable.tsx      # Task 8
      GlossaryTerm.tsx                 # Task 9
    lib/
      api.ts                           # unchanged (already complete)
      format.ts                        # Task 2: formatSignedInr if needed
      windows.ts                       # Task 2: NEW — window/metric pickers
      allocation.ts                    # Task 2: NEW — kind buckets
      status.ts                        # Task 2: NEW — banner derivation
      import-report.ts                 # Task 7: sessionStorage helpers
      glossary.ts                      # Task 9: term content
    __tests__/
      windows.test.ts                  # Task 2
      allocation.test.ts               # Task 2
      status.test.ts                   # Task 2
      AppShell.test.tsx                # Task 1
      WindowSelect.test.tsx            # Task 3
      StatusBanner.test.tsx            # Task 3
      OverviewCards.test.tsx           # Task 4
      HoldingsTable.test.tsx           # Task 5
      ImportReport.test.tsx            # Task 7
      SettingsAuth.test.tsx            # Task 8
      glossary.test.ts                 # Task 9
```

---

### Task 1: Theme tokens, test deps, AppShell

**Files:**
- Modify: `apps/web/package.json`
- Modify: `apps/web/vitest.config.ts`
- Modify: `apps/web/src/app/globals.css`
- Modify: `apps/web/src/app/layout.tsx`
- Create: `apps/web/src/components/AppShell.tsx`
- Create: `apps/web/src/__tests__/AppShell.test.tsx`
- Create stub pages (minimal headings) so nav links resolve:
  - `apps/web/src/app/holdings/page.tsx`
  - `apps/web/src/app/import/page.tsx`
  - `apps/web/src/app/settings/page.tsx`
  - `apps/web/src/app/glossary/page.tsx`

**Interfaces:**
- Consumes: Next.js App Router `children`
- Produces: `AppShell({ children })` with collapsible nav; CSS vars `--bg`, `--surface`, `--border`, `--text`, `--muted`, `--positive`, `--warn`, `--accent`

- [ ] **Step 1: Install deps**

```bash
cd apps/web && npm install recharts && npm install -D @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

Expected: packages in `package.json`; lockfile updated.

- [ ] **Step 2: Configure Vitest for jsdom + jest-dom**

Replace `apps/web/vitest.config.ts` with:

```ts
import path from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    setupFiles: ["./vitest.setup.ts"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

Create `apps/web/vitest.setup.ts`:

```ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 3: Write failing AppShell test**

Create `apps/web/src/__tests__/AppShell.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AppShell } from "@/components/AppShell";

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}));

describe("AppShell", () => {
  it("renders brand and five nav items", () => {
    render(
      <AppShell>
        <p>child</p>
      </AppShell>,
    );
    expect(screen.getByText("Portfolio Tracker")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /overview/i })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: /holdings/i })).toHaveAttribute("href", "/holdings");
    expect(screen.getByRole("link", { name: /import/i })).toHaveAttribute("href", "/import");
    expect(screen.getByRole("link", { name: /settings/i })).toHaveAttribute("href", "/settings");
    expect(screen.getByRole("link", { name: /glossary/i })).toHaveAttribute("href", "/glossary");
    expect(screen.getByText("child")).toBeInTheDocument();
  });

  it("collapses nav to data-collapsed", async () => {
    const user = userEvent.setup();
    render(
      <AppShell>
        <p>child</p>
      </AppShell>,
    );
    const toggle = screen.getByRole("button", { name: /collapse|expand/i });
    await user.click(toggle);
    expect(screen.getByTestId("app-shell")).toHaveAttribute("data-collapsed", "true");
  });
});
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd apps/web && npm test -- src/__tests__/AppShell.test.tsx`

Expected: FAIL — cannot find `AppShell` module.

- [ ] **Step 5: Dark theme CSS + AppShell + layout + stub routes**

`apps/web/src/app/globals.css`:

```css
*,
*::before,
*::after {
  box-sizing: border-box;
}

:root {
  --bg: #0f1419;
  --surface: #1a222d;
  --surface-2: #232d3b;
  --border: #2e3a4a;
  --text: #e8eef6;
  --muted: #8b9bb0;
  --positive: #3ecf8e;
  --negative: #f07178;
  --warn: #e6a23c;
  --accent: #5b9fd4;
  --nav-width: 220px;
  --nav-collapsed: 64px;
  --font: "IBM Plex Sans", "Segoe UI", sans-serif;
}

html,
body {
  margin: 0;
  padding: 0;
  min-height: 100%;
  background: radial-gradient(1200px 600px at 10% -10%, #1a2a3a 0%, var(--bg) 55%);
  color: var(--text);
  font-family: var(--font);
}

a {
  color: inherit;
  text-decoration: none;
}

button,
select,
input {
  font: inherit;
}

.app-shell {
  display: grid;
  grid-template-columns: var(--nav-width) 1fr;
  min-height: 100vh;
}

.app-shell[data-collapsed="true"] {
  grid-template-columns: var(--nav-collapsed) 1fr;
}

.app-nav {
  border-right: 1px solid var(--border);
  background: color-mix(in srgb, var(--surface) 92%, black);
  padding: 1rem 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.app-brand {
  font-weight: 650;
  letter-spacing: 0.02em;
  padding: 0.25rem 0.5rem;
  white-space: nowrap;
  overflow: hidden;
}

.app-nav nav {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.app-nav a {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.55rem 0.65rem;
  border-radius: 8px;
  color: var(--muted);
}

.app-nav a[data-active="true"] {
  background: var(--surface-2);
  color: var(--text);
}

.app-main {
  padding: 1.5rem 1.75rem 3rem;
  max-width: 1200px;
}

.app-shell[data-collapsed="true"] .nav-label {
  display: none;
}

.nav-toggle {
  margin-top: auto;
  background: transparent;
  border: 1px solid var(--border);
  color: var(--muted);
  border-radius: 8px;
  padding: 0.45rem 0.6rem;
  cursor: pointer;
}
```

`apps/web/src/components/AppShell.tsx`:

```tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const NAV = [
  { href: "/", label: "Overview", icon: "◉" },
  { href: "/holdings", label: "Holdings", icon: "☰" },
  { href: "/import", label: "Import", icon: "↑" },
  { href: "/settings", label: "Settings", icon: "⚙" },
  { href: "/glossary", label: "Glossary", icon: "?" },
] as const;

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="app-shell" data-testid="app-shell" data-collapsed={collapsed ? "true" : "false"}>
      <aside className="app-nav">
        <div className="app-brand">
          <span className="nav-label">Portfolio Tracker</span>
          {collapsed ? <span aria-hidden>PT</span> : null}
        </div>
        <nav aria-label="Primary">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              data-active={isActive(pathname, item.href) ? "true" : "false"}
            >
              <span aria-hidden>{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </Link>
          ))}
        </nav>
        <button
          type="button"
          className="nav-toggle"
          aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}
          onClick={() => setCollapsed((v) => !v)}
        >
          <span className="nav-label">{collapsed ? "Expand" : "Collapse"}</span>
          <span aria-hidden>{collapsed ? "»" : "«"}</span>
        </button>
      </aside>
      <main className="app-main">{children}</main>
    </div>
  );
}
```

`apps/web/src/app/layout.tsx`:

```tsx
import type { Metadata } from "next";
import { AppShell } from "@/components/AppShell";
import "./globals.css";

export const metadata: Metadata = {
  title: "Portfolio Tracker",
  description: "Local Zerodha equity + Coin MF tracker",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
```

Stub each of holdings/import/settings/glossary pages as:

```tsx
export default function Page() {
  return <h1>Holdings</h1>; // Import / Settings / Glossary respectively
}
```

Leave `page.tsx` Overview stub for Task 4 (may still say placeholder).

- [ ] **Step 6: Run tests**

Run: `cd apps/web && npm test`

Expected: PASS (including existing `api` / `format` tests under jsdom).

- [ ] **Step 7: Commit**

```bash
git add apps/web/package.json apps/web/package-lock.json apps/web/vitest.config.ts apps/web/vitest.setup.ts \
  apps/web/src/app/globals.css apps/web/src/app/layout.tsx apps/web/src/components/AppShell.tsx \
  apps/web/src/__tests__/AppShell.test.tsx \
  apps/web/src/app/holdings/page.tsx apps/web/src/app/import/page.tsx \
  apps/web/src/app/settings/page.tsx apps/web/src/app/glossary/page.tsx
git commit -m "$(cat <<'EOF'
feat(web): add dark AppShell and nav routes

EOF
)"
```

---

### Task 2: Window / metric / allocation / status helpers

**Files:**
- Create: `apps/web/src/lib/windows.ts`
- Create: `apps/web/src/lib/allocation.ts`
- Create: `apps/web/src/lib/status.ts`
- Create: `apps/web/src/__tests__/windows.test.ts`
- Create: `apps/web/src/__tests__/allocation.test.ts`
- Create: `apps/web/src/__tests__/status.test.ts`
- Modify: `apps/web/src/lib/format.ts` (add `formatSignedInr`)

**Interfaces:**
- Consumes: `Overview["windows"]`, `Holding` from `@/lib/api`
- Produces:
  - `export type WindowKey = "ITD" | "1Y" | "3Y" | "5Y"`
  - `export type MetricKey = "absolute" | "xirr" | "cagr"`
  - `getWindowMetrics(windows, key): WindowMetrics | null`
  - `pickReturnPct(metrics, metric): number | null`
  - `pickExcessPp(metrics, metric): number | null`
  - `pickBenchmarkReturn(metrics): number | null`
  - `allocationByKind(holdings): { label: string; weight: number }[]`
  - `deriveStatusBanner(input): StatusBannerModel | null`

- [ ] **Step 1: Write failing tests**

`apps/web/src/__tests__/windows.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import {
  getWindowMetrics,
  pickBenchmarkReturn,
  pickExcessPp,
  pickReturnPct,
} from "@/lib/windows";

const windows = {
  ITD: {
    absolute_pct: 0.2,
    absolute_inr: 100,
    xirr: 0.15,
    cagr: 0.12,
    benchmark_return: 0.1,
    absolute_excess_pp: 5,
    xirr_excess_pp: 2.5,
    cagr_excess_pp: 1.1,
  },
  "1Y": null,
  "3Y": null,
  "5Y": null,
} as const;

describe("windows helpers", () => {
  it("reads named window including 1Y alias key", () => {
    expect(getWindowMetrics(windows, "ITD")?.xirr).toBe(0.15);
    expect(getWindowMetrics(windows, "1Y")).toBeNull();
  });

  it("picks return / excess / benchmark by metric", () => {
    const m = getWindowMetrics(windows, "ITD");
    expect(pickReturnPct(m, "xirr")).toBe(0.15);
    expect(pickReturnPct(m, "absolute")).toBe(0.2);
    expect(pickReturnPct(m, "cagr")).toBe(0.12);
    expect(pickExcessPp(m, "xirr")).toBe(2.5);
    expect(pickBenchmarkReturn(m)).toBe(0.1);
  });

  it("returns null when window missing", () => {
    expect(pickReturnPct(null, "xirr")).toBeNull();
    expect(pickExcessPp(null, "absolute")).toBeNull();
  });
});
```

`apps/web/src/__tests__/allocation.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { allocationByKind } from "@/lib/allocation";
import type { Holding } from "@/lib/api";

function h(partial: Partial<Holding> & Pick<Holding, "instrument_type" | "value">): Holding {
  return {
    instrument_id: 1,
    symbol: "X",
    qty: 1,
    avg_price: 1,
    ltp: 1,
    absolute_pct: null,
    absolute_inr: null,
    xirr: null,
    cagr: null,
    benchmark: "Nifty 500",
    benchmark_return: null,
    absolute_excess_pp: null,
    xirr_excess_pp: null,
    cagr_excess_pp: null,
    incomplete: false,
    needs_category: false,
    mf_category: null,
    windows: { ITD: null, "1Y": null, "3Y": null, "5Y": null },
    ...partial,
  };
}

describe("allocationByKind", () => {
  it("aggregates equity / mf / etf weights", () => {
    const slices = allocationByKind([
      h({ instrument_type: "equity", value: 50 }),
      h({ instrument_type: "mf", value: 30 }),
      h({ instrument_type: "etf", value: 20 }),
    ]);
    expect(slices).toEqual([
      { label: "Equity", weight: 0.5 },
      { label: "Mutual funds", weight: 0.3 },
      { label: "ETFs", weight: 0.2 },
    ]);
  });

  it("omits zero buckets and handles empty", () => {
    expect(allocationByKind([h({ instrument_type: "equity", value: 10 })])).toEqual([
      { label: "Equity", weight: 1 },
    ]);
    expect(allocationByKind([])).toEqual([]);
  });
});
```

`apps/web/src/__tests__/status.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { deriveStatusBanner } from "@/lib/status";

describe("deriveStatusBanner", () => {
  it("prompts login when disconnected", () => {
    const banner = deriveStatusBanner({
      connected: false,
      lastSyncAt: null,
      incomplete: false,
      gap: null,
      today: "2026-08-02",
    });
    expect(banner?.kind).toBe("login");
    expect(banner?.ctaHref).toBe("/settings");
  });

  it("links import when gap present", () => {
    const banner = deriveStatusBanner({
      connected: true,
      lastSyncAt: "2026-08-02T10:00:00+05:30",
      incomplete: false,
      gap: { suggested_from: "2024-01-01", suggested_to: "2024-06-01", message: "gap" },
      today: "2026-08-02",
    });
    expect(banner?.kind).toBe("gap");
    expect(banner?.ctaHref).toBe("/import");
  });

  it("flags outdated when last sync day is before today", () => {
    const banner = deriveStatusBanner({
      connected: true,
      lastSyncAt: "2026-08-01T18:00:00+05:30",
      incomplete: false,
      gap: null,
      today: "2026-08-02",
    });
    expect(banner?.kind).toBe("outdated");
    expect(banner?.ctaLabel).toMatch(/refresh holdings/i);
  });

  it("flags incomplete metrics as outdated", () => {
    const banner = deriveStatusBanner({
      connected: true,
      lastSyncAt: "2026-08-02T09:00:00+05:30",
      incomplete: true,
      gap: null,
      today: "2026-08-02",
    });
    expect(banner?.kind).toBe("outdated");
  });

  it("returns null when healthy", () => {
    expect(
      deriveStatusBanner({
        connected: true,
        lastSyncAt: "2026-08-02T09:00:00+05:30",
        incomplete: false,
        gap: null,
        today: "2026-08-02",
      }),
    ).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/web && npm test -- src/__tests__/windows.test.ts src/__tests__/allocation.test.ts src/__tests__/status.test.ts`

Expected: FAIL — modules not found.

- [ ] **Step 3: Implement helpers**

`apps/web/src/lib/windows.ts`:

```ts
import type { Overview } from "@/lib/api";

export type WindowKey = "ITD" | "1Y" | "3Y" | "5Y";
export type MetricKey = "absolute" | "xirr" | "cagr";

export const WINDOW_KEYS: WindowKey[] = ["ITD", "1Y", "3Y", "5Y"];
export const METRIC_KEYS: MetricKey[] = ["absolute", "xirr", "cagr"];

export type WindowsMap = Overview["windows"];
export type WindowMetrics = NonNullable<WindowsMap["ITD"]>;

export function getWindowMetrics(
  windows: WindowsMap,
  key: WindowKey,
): WindowMetrics | null {
  return windows[key] ?? null;
}

export function pickReturnPct(
  metrics: WindowMetrics | null,
  metric: MetricKey,
): number | null {
  if (!metrics) return null;
  if (metric === "absolute") return metrics.absolute_pct ?? null;
  if (metric === "xirr") return metrics.xirr ?? null;
  return metrics.cagr ?? null;
}

export function pickExcessPp(
  metrics: WindowMetrics | null,
  metric: MetricKey,
): number | null {
  if (!metrics) return null;
  if (metric === "absolute") return metrics.absolute_excess_pp ?? null;
  if (metric === "xirr") return metrics.xirr_excess_pp ?? null;
  return metrics.cagr_excess_pp ?? null;
}

export function pickBenchmarkReturn(metrics: WindowMetrics | null): number | null {
  return metrics?.benchmark_return ?? null;
}

export function metricLabel(metric: MetricKey): string {
  if (metric === "absolute") return "Absolute";
  if (metric === "xirr") return "XIRR";
  return "CAGR";
}
```

`apps/web/src/lib/allocation.ts`:

```ts
import type { Holding } from "@/lib/api";

export type AllocationSliceUi = { label: string; weight: number };

export function allocationByKind(holdings: Holding[]): AllocationSliceUi[] {
  let equity = 0;
  let mf = 0;
  let etf = 0;
  for (const h of holdings) {
    const v = h.value ?? 0;
    if (h.instrument_type === "mf") mf += v;
    else if (h.instrument_type === "etf") etf += v;
    else equity += v;
  }
  const total = equity + mf + etf;
  if (!total) return [];
  return [
    { label: "Equity", weight: equity / total },
    { label: "Mutual funds", weight: mf / total },
    { label: "ETFs", weight: etf / total },
  ].filter((s) => s.weight > 0);
}
```

`apps/web/src/lib/status.ts`:

```ts
export type StatusBannerModel = {
  kind: "login" | "gap" | "outdated";
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
  const outdated = input.incomplete || !day || day < input.today;
  if (outdated) {
    return {
      kind: "outdated",
      message: "Holdings may be outdated",
      ctaLabel: "Refresh holdings",
      ctaAction: "refresh",
      disabled: !input.connected,
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
```

Append to `apps/web/src/lib/format.ts`:

```ts
export function formatSignedInr(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "N/A";
  if (value === 0) return formatInr(0);
  const sign = value > 0 ? "+" : "−";
  return `${sign}${formatInr(Math.abs(value))}`;
}
```

Add a small test in `format.test.ts` for `formatSignedInr(100)` containing `+` and `₹`.

- [ ] **Step 4: Run tests**

Run: `cd apps/web && npm test -- src/__tests__/windows.test.ts src/__tests__/allocation.test.ts src/__tests__/status.test.ts src/__tests__/format.test.ts`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/lib/windows.ts apps/web/src/lib/allocation.ts apps/web/src/lib/status.ts \
  apps/web/src/lib/format.ts apps/web/src/__tests__/windows.test.ts \
  apps/web/src/__tests__/allocation.test.ts apps/web/src/__tests__/status.test.ts \
  apps/web/src/__tests__/format.test.ts
git commit -m "$(cat <<'EOF'
feat(web): add window, allocation, and status helpers

EOF
)"
```

---

### Task 3: WindowSelect, MetricWindowSelects, StatusBanner

**Files:**
- Create: `apps/web/src/components/WindowSelect.tsx`
- Create: `apps/web/src/components/MetricWindowSelects.tsx`
- Create: `apps/web/src/components/StatusBanner.tsx`
- Create: `apps/web/src/__tests__/WindowSelect.test.tsx`
- Create: `apps/web/src/__tests__/StatusBanner.test.tsx`
- Modify: `apps/web/src/app/globals.css` (banner + control styles)

**Interfaces:**
- Consumes: `WindowKey`, `MetricKey`, `StatusBannerModel`, `api.postSync`
- Produces: controlled selects that call `onChange`; StatusBanner invokes refresh or navigates

- [ ] **Step 1: Write failing tests**

`apps/web/src/__tests__/WindowSelect.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { WindowSelect } from "@/components/WindowSelect";
import { MetricWindowSelects } from "@/components/MetricWindowSelects";

describe("WindowSelect", () => {
  it("calls onChange with window key", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<WindowSelect value="ITD" onChange={onChange} />);
    await user.selectOptions(screen.getByLabelText(/window/i), "1Y");
    expect(onChange).toHaveBeenCalledWith("1Y");
  });
});

describe("MetricWindowSelects", () => {
  it("emits metric and window changes", async () => {
    const user = userEvent.setup();
    const onMetric = vi.fn();
    const onWindow = vi.fn();
    render(
      <MetricWindowSelects
        metric="xirr"
        window="ITD"
        onMetricChange={onMetric}
        onWindowChange={onWindow}
      />,
    );
    await user.selectOptions(screen.getByLabelText(/metric/i), "cagr");
    expect(onMetric).toHaveBeenCalledWith("cagr");
    await user.selectOptions(screen.getByLabelText(/window/i), "3Y");
    expect(onWindow).toHaveBeenCalledWith("3Y");
  });
});
```

`apps/web/src/__tests__/StatusBanner.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StatusBanner } from "@/components/StatusBanner";

describe("StatusBanner", () => {
  it("disables refresh when model.disabled", () => {
    render(
      <StatusBanner
        model={{
          kind: "outdated",
          message: "Holdings may be outdated",
          ctaLabel: "Refresh holdings",
          ctaAction: "refresh",
          disabled: true,
        }}
        onRefresh={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: /refresh holdings/i })).toBeDisabled();
  });

  it("fires onRefresh for outdated CTA", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn();
    render(
      <StatusBanner
        model={{
          kind: "outdated",
          message: "Holdings may be outdated",
          ctaLabel: "Refresh holdings",
          ctaAction: "refresh",
        }}
        onRefresh={onRefresh}
      />,
    );
    await user.click(screen.getByRole("button", { name: /refresh holdings/i }));
    expect(onRefresh).toHaveBeenCalled();
  });

  it("renders link CTA for gap", () => {
    render(
      <StatusBanner
        model={{
          kind: "gap",
          message: "gap",
          ctaLabel: "Open Import",
          ctaHref: "/import",
        }}
        onRefresh={vi.fn()}
      />,
    );
    expect(screen.getByRole("link", { name: /open import/i })).toHaveAttribute(
      "href",
      "/import",
    );
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/web && npm test -- src/__tests__/WindowSelect.test.tsx src/__tests__/StatusBanner.test.tsx`

Expected: FAIL — components missing.

- [ ] **Step 3: Implement components**

`apps/web/src/components/WindowSelect.tsx`:

```tsx
"use client";

import { WINDOW_KEYS, type WindowKey } from "@/lib/windows";

type Props = {
  value: WindowKey;
  onChange: (w: WindowKey) => void;
  id?: string;
};

export function WindowSelect({ value, onChange, id = "window" }: Props) {
  return (
    <label className="field">
      <span>Window</span>
      <select
        id={id}
        aria-label="Window"
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
```

`apps/web/src/components/MetricWindowSelects.tsx`:

```tsx
"use client";

import {
  METRIC_KEYS,
  metricLabel,
  type MetricKey,
  type WindowKey,
} from "@/lib/windows";
import { WindowSelect } from "@/components/WindowSelect";

type Props = {
  metric: MetricKey;
  window: WindowKey;
  onMetricChange: (m: MetricKey) => void;
  onWindowChange: (w: WindowKey) => void;
};

export function MetricWindowSelects({
  metric,
  window,
  onMetricChange,
  onWindowChange,
}: Props) {
  return (
    <div className="control-row">
      <label className="field">
        <span>Metric</span>
        <select
          aria-label="Metric"
          value={metric}
          onChange={(e) => onMetricChange(e.target.value as MetricKey)}
        >
          {METRIC_KEYS.map((k) => (
            <option key={k} value={k}>
              {metricLabel(k)}
            </option>
          ))}
        </select>
      </label>
      <WindowSelect value={window} onChange={onWindowChange} />
    </div>
  );
}
```

`apps/web/src/components/StatusBanner.tsx`:

```tsx
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
```

Add CSS for `.status-banner`, `.field`, `.control-row` in `globals.css` (warn border for outdated/gap; muted for login).

- [ ] **Step 4: Run tests**

Run: `cd apps/web && npm test -- src/__tests__/WindowSelect.test.tsx src/__tests__/StatusBanner.test.tsx`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/components/WindowSelect.tsx apps/web/src/components/MetricWindowSelects.tsx \
  apps/web/src/components/StatusBanner.tsx apps/web/src/__tests__/WindowSelect.test.tsx \
  apps/web/src/__tests__/StatusBanner.test.tsx apps/web/src/app/globals.css
git commit -m "$(cat <<'EOF'
feat(web): add Window/Metric controls and StatusBanner

EOF
)"
```

---

### Task 4: Overview page (hero, cards, chart, allocation)

**Files:**
- Create: `apps/web/src/components/ValueHero.tsx`
- Create: `apps/web/src/components/MetricCard.tsx`
- Create: `apps/web/src/components/AllocationChart.tsx`
- Create: `apps/web/src/components/ReturnSeriesChart.tsx`
- Create: `apps/web/src/components/OverviewPage.tsx` (client orchestrator)
- Modify: `apps/web/src/app/page.tsx`
- Create: `apps/web/src/__tests__/OverviewCards.test.tsx`

**Interfaces:**
- Consumes: `api.getOverview`, `getHoldings`, `getAlerts`, `getAuthStatus`, `getPortfolioSeries`, `postSync`; helpers from Task 2–3
- Produces: Overview landing matching spec §5.1

- [ ] **Step 1: Write failing card tests**

`apps/web/src/__tests__/OverviewCards.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MetricCard } from "@/components/MetricCard";
import { ValueHero } from "@/components/ValueHero";

describe("ValueHero", () => {
  it("shows value, invested, and absolute return", () => {
    render(
      <ValueHero
        totalValue={250000}
        investedCost={200000}
        gainInr={50000}
        gainPct={0.25}
      />,
    );
    expect(screen.getByText(/total portfolio value/i)).toBeInTheDocument();
    expect(screen.getByText(/25\.00%/)).toBeInTheDocument();
  });

  it("shows N/A for null gain pct", () => {
    render(
      <ValueHero totalValue={0} investedCost={0} gainInr={0} gainPct={null} />,
    );
    expect(screen.getAllByText("N/A").length).toBeGreaterThan(0);
  });
});

describe("MetricCard", () => {
  it("updates displayed value when Metric changes", async () => {
    const user = userEvent.setup();
    render(
      <MetricCard
        title="Portfolio return"
        windows={{
          ITD: {
            absolute_pct: 0.2,
            absolute_inr: 1,
            xirr: 0.18,
            cagr: 0.1,
            benchmark_return: 0.12,
            absolute_excess_pp: 1,
            xirr_excess_pp: 2,
            cagr_excess_pp: 3,
          },
          "1Y": null,
          "3Y": null,
          "5Y": null,
        }}
        mode="return"
        defaultMetric="xirr"
      />,
    );
    expect(screen.getByText("18.00%")).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText(/metric/i), "cagr");
    expect(screen.getByText("10.00%")).toBeInTheDocument();
  });

  it("shows outperformance copy and N/A when missing", async () => {
    render(
      <MetricCard
        title="Outperformance"
        windows={{
          ITD: null,
          "1Y": null,
          "3Y": null,
          "5Y": null,
        }}
        mode="outperformance"
        defaultMetric="xirr"
      />,
    );
    expect(screen.getByText(/category benchmarks/i)).toBeInTheDocument();
    expect(screen.getByText("N/A")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/web && npm test -- src/__tests__/OverviewCards.test.tsx`

Expected: FAIL — components missing.

- [ ] **Step 3: Implement Overview components + page**

`ValueHero.tsx` — presentational; uses `formatInr`, `formatSignedInr`, `formatPct`.

`MetricCard.tsx` — client; local state `metric` (default from prop) + `window` (default `ITD`); `mode="return"` uses `pickReturnPct` + `formatPct`; `mode="outperformance"` uses `pickExcessPp` + `formatPp`, subtitle “you beat category benchmarks by …”, optional breakdown line when `pickReturnPct` and `pickBenchmarkReturn` both non-null: show `formatPct(port)` − `formatPct(bench)`.

`AllocationChart.tsx` — client; Recharts `PieChart`/`Pie`/`Tooltip`/`Legend`; props `slices: AllocationSliceUi[]`; empty state “No holdings yet”.

`ReturnSeriesChart.tsx` — client; props:

```ts
type Props = {
  title: string;
  available: boolean;
  metricSupportsSeries: boolean; // false for xirr/cagr
  points: { date: string; portfolio: number | null; benchmark: number | null }[];
  portfolioLabel?: string;
  benchmarkLabel?: string;
};
```

When `!metricSupportsSeries` show: “Series chart supports Absolute return only for v1.”  
When `!available` show: “N/A — not enough history for this window.”  
Else Recharts `LineChart` with X=`date`, Y percent (`value * 100`), axes, tooltip with date + both series.

`OverviewPage.tsx` (client):

```tsx
"use client";

import { useEffect, useState } from "react";
import { api, type Alerts, type AuthStatus, type Holding, type Overview, type PortfolioSeries } from "@/lib/api";
import { allocationByKind } from "@/lib/allocation";
import { deriveStatusBanner, todayIst } from "@/lib/status";
import type { MetricKey, WindowKey } from "@/lib/windows";
import { StatusBanner } from "@/components/StatusBanner";
import { ValueHero } from "@/components/ValueHero";
import { MetricCard } from "@/components/MetricCard";
import { AllocationChart } from "@/components/AllocationChart";
import { ReturnSeriesChart } from "@/components/ReturnSeriesChart";
import { MetricWindowSelects } from "@/components/MetricWindowSelects";

export function OverviewPage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [auth, setAuth] = useState<AuthStatus | null>(null);
  const [alerts, setAlerts] = useState<Alerts | null>(null);
  const [series, setSeries] = useState<PortfolioSeries | null>(null);
  const [chartMetric, setChartMetric] = useState<MetricKey>("absolute");
  const [chartWindow, setChartWindow] = useState<WindowKey>("ITD");
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  async function loadCore() {
    const [o, h, a, al] = await Promise.all([
      api.getOverview(),
      api.getHoldings(),
      api.getAuthStatus(),
      api.getAlerts(),
    ]);
    setOverview(o);
    setHoldings(h);
    setAuth(a);
    setAlerts(al);
  }

  useEffect(() => {
    void loadCore().catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    if (chartMetric !== "absolute") {
      setSeries(null);
      return;
    }
    void api
      .getPortfolioSeries(chartWindow)
      .then(setSeries)
      .catch((e: Error) => setError(e.message));
  }, [chartMetric, chartWindow]);

  async function onRefresh() {
    setRefreshing(true);
    try {
      await api.postSync();
      await loadCore();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sync failed");
    } finally {
      setRefreshing(false);
    }
  }

  if (error) return <p role="alert">{error}</p>;
  if (!overview || !auth || !alerts) return <p>Loading…</p>;

  const banner = deriveStatusBanner({
    connected: auth.connected,
    lastSyncAt: auth.last_sync_at,
    incomplete: overview.incomplete,
    gap: alerts.gap,
    today: todayIst(),
  });

  return (
    <div className="stack">
      <h1>Overview</h1>
      <StatusBanner model={banner} onRefresh={onRefresh} refreshing={refreshing} />
      <ValueHero
        totalValue={overview.total_value}
        investedCost={overview.absolute.invested_cost}
        gainInr={overview.absolute.gain_inr}
        gainPct={overview.absolute.gain_pct}
      />
      <div className="card-grid">
        <MetricCard
          title="Portfolio return"
          windows={overview.windows}
          mode="return"
          defaultMetric="xirr"
        />
        <MetricCard
          title="Outperformance"
          windows={overview.windows}
          mode="outperformance"
          defaultMetric="xirr"
        />
      </div>
      <section className="panel">
        <div className="panel-head">
          <h2>Portfolio vs category benchmarks</h2>
          <MetricWindowSelects
            metric={chartMetric}
            window={chartWindow}
            onMetricChange={setChartMetric}
            onWindowChange={setChartWindow}
          />
        </div>
        <ReturnSeriesChart
          title="Portfolio vs category benchmarks"
          available={series?.available ?? false}
          metricSupportsSeries={chartMetric === "absolute"}
          points={(series?.points ?? []).map((p) => ({
            date: p.date,
            portfolio: p.portfolio_return ?? null,
            benchmark: p.benchmark_return ?? null,
          }))}
          portfolioLabel="Portfolio"
          benchmarkLabel="Category benchmarks (market-weighted)"
        />
      </section>
      <section className="panel">
        <h2>Asset allocation</h2>
        <AllocationChart slices={allocationByKind(holdings)} />
      </section>
    </div>
  );
}
```

`apps/web/src/app/page.tsx`:

```tsx
import { OverviewPage } from "@/components/OverviewPage";

export default function HomePage() {
  return <OverviewPage />;
}
```

Implement presentational pieces fully (labels from spec). Add `.stack`, `.card-grid`, `.panel` CSS.

- [ ] **Step 4: Run tests**

Run: `cd apps/web && npm test -- src/__tests__/OverviewCards.test.tsx`

Expected: PASS. Also `npm test` full suite green.

- [ ] **Step 5: Manual smoke (optional if API up)**

Run API + web; open `/`; confirm hero numbers and Window change on cards.

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/components/ValueHero.tsx apps/web/src/components/MetricCard.tsx \
  apps/web/src/components/AllocationChart.tsx apps/web/src/components/ReturnSeriesChart.tsx \
  apps/web/src/components/OverviewPage.tsx apps/web/src/app/page.tsx \
  apps/web/src/__tests__/OverviewCards.test.tsx apps/web/src/app/globals.css
git commit -m "$(cat <<'EOF'
feat(web): ship Overview with returns, chart, and allocation

EOF
)"
```

---

### Task 5: Holdings tables + page Window

**Files:**
- Create: `apps/web/src/components/HoldingsTable.tsx`
- Create: `apps/web/src/components/HoldingsPage.tsx`
- Modify: `apps/web/src/app/holdings/page.tsx`
- Create: `apps/web/src/__tests__/HoldingsTable.test.tsx`

**Interfaces:**
- Consumes: `api.getHoldings()`, `getWindowMetrics` / pick helpers, `format*`
- Produces: two tables; row navigates to `/holdings/[instrument_id]`

- [ ] **Step 1: Write failing test**

```tsx
import { render, screen } from "@testing-library/react";
import { HoldingsTable } from "@/components/HoldingsTable";
import type { Holding } from "@/lib/api";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

const base = {
  qty: 2,
  avg_price: 100,
  ltp: 120,
  value: 240,
  absolute_pct: null,
  absolute_inr: null,
  xirr: null,
  cagr: null,
  benchmark: "Nifty 500",
  benchmark_return: null,
  absolute_excess_pp: null,
  xirr_excess_pp: null,
  cagr_excess_pp: null,
  incomplete: false,
  needs_category: false,
  mf_category: null,
  windows: {
    ITD: {
      absolute_pct: 0.1,
      absolute_inr: 20,
      xirr: 0.12,
      cagr: null,
      benchmark_return: 0.08,
      absolute_excess_pp: 2,
      xirr_excess_pp: 1.5,
      cagr_excess_pp: null,
    },
    "1Y": null,
    "3Y": null,
    "5Y": null,
  },
} as const;

describe("HoldingsTable", () => {
  it("renders Abs % XIRR CAGR Outperf and N/A for missing CAGR", () => {
    const rows: Holding[] = [
      {
        ...base,
        instrument_id: 1,
        symbol: "RELIANCE",
        instrument_type: "equity",
      },
    ];
    render(
      <HoldingsTable
        title="Stocks & ETFs"
        variant="equity"
        rows={rows}
        windowKey="ITD"
      />,
    );
    expect(screen.getByText("RELIANCE")).toBeInTheDocument();
    expect(screen.getByText("10.00%")).toBeInTheDocument();
    expect(screen.getByText("12.00%")).toBeInTheDocument();
    expect(screen.getByText("N/A")).toBeInTheDocument(); // CAGR
    expect(screen.getByText("+2.00 pp")).toBeInTheDocument(); // absolute_excess_pp
  });
});
```

**Column rule (locked):** Outperf. (pp) = selected window’s `absolute_excess_pp` (null → N/A). Abs % / XIRR / CAGR come from the same window’s `absolute_pct` / `xirr` / `cagr`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/web && npm test -- src/__tests__/HoldingsTable.test.tsx`

Expected: FAIL.

- [ ] **Step 3: Implement HoldingsTable + HoldingsPage**

`HoldingsTable` columns:

| variant | identity cols | price col |
| ------- | ------------- | --------- |
| `equity` | Symbol | LTP |
| `mf` | Symbol, Category (`mf_category` or “—” ) | NAV (`ltp`) |

Shared: Qty, Avg, Value, Abs %, XIRR, CAGR, Outperf. (pp).  
Click row → `router.push(`/holdings/${instrument_id}`)`.  
Null metrics → `N/A`.

`HoldingsPage`:

```tsx
"use client";

import { useEffect, useMemo, useState } from "react";
import { api, type Holding } from "@/lib/api";
import { WindowSelect } from "@/components/WindowSelect";
import { HoldingsTable } from "@/components/HoldingsTable";
import type { WindowKey } from "@/lib/windows";

export function HoldingsPage() {
  const [rows, setRows] = useState<Holding[] | null>(null);
  const [windowKey, setWindowKey] = useState<WindowKey>("ITD");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void api.getHoldings().then(setRows).catch((e: Error) => setError(e.message));
  }, []);

  const { equityEtfs, mfs } = useMemo(() => {
    const list = rows ?? [];
    return {
      equityEtfs: list.filter((h) => h.instrument_type !== "mf"),
      mfs: list.filter((h) => h.instrument_type === "mf"),
    };
  }, [rows]);

  if (error) return <p role="alert">{error}</p>;
  if (!rows) return <p>Loading…</p>;

  return (
    <div className="stack">
      <div className="panel-head">
        <h1>Holdings</h1>
        <WindowSelect value={windowKey} onChange={setWindowKey} />
      </div>
      <HoldingsTable
        title="Stocks & ETFs"
        variant="equity"
        rows={equityEtfs}
        windowKey={windowKey}
      />
      <HoldingsTable
        title="Mutual funds"
        variant="mf"
        rows={mfs}
        windowKey={windowKey}
      />
    </div>
  );
}
```

Wire `apps/web/src/app/holdings/page.tsx` → `<HoldingsPage />`.

- [ ] **Step 4: Run tests**

Run: `cd apps/web && npm test -- src/__tests__/HoldingsTable.test.tsx`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/components/HoldingsTable.tsx apps/web/src/components/HoldingsPage.tsx \
  apps/web/src/app/holdings/page.tsx apps/web/src/__tests__/HoldingsTable.test.tsx
git commit -m "$(cat <<'EOF'
feat(web): add Holdings tables with windowed return columns

EOF
)"
```

---

### Task 6: Holding detail (chart + transactions)

**Files:**
- Create: `apps/web/src/components/TransactionsTable.tsx`
- Create: `apps/web/src/components/HoldingDetailPage.tsx`
- Create: `apps/web/src/app/holdings/[id]/page.tsx`

**Interfaces:**
- Consumes: `api.getHolding`, `getHoldingTransactions`, `getHoldingSeries`
- Produces: detail layout §5.3; Window on own row; returns chips; chart; transactions

- [ ] **Step 1: Write failing TransactionsTable test**

Create `apps/web/src/__tests__/TransactionsTable.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { TransactionsTable } from "@/components/TransactionsTable";

describe("TransactionsTable", () => {
  it("renders date side qty price amount source labels", () => {
    render(
      <TransactionsTable
        rows={[
          {
            id: 1,
            trade_date: "2024-01-10",
            side: "buy",
            quantity: 5,
            price: 2000,
            fees: 10,
            amount: 10000,
            source: "csv",
          },
        ]}
      />,
    );
    expect(screen.getByText("2024-01-10")).toBeInTheDocument();
    expect(screen.getByText("buy")).toBeInTheDocument();
    expect(screen.getByText("csv")).toBeInTheDocument();
    expect(screen.getByText(/10,000/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/web && npm test -- src/__tests__/TransactionsTable.test.tsx`

Expected: FAIL.

- [ ] **Step 3: Implement detail page**

`TransactionsTable` — columns: Date, Side, Qty, Price, Amount, Source (map `csv`→`CSV`, `api`→`API`).

`HoldingDetailPage` (client), props `{ instrumentId: number }`:

1. Load holding + transactions in parallel.
2. Header: ← Link to `/holdings`; symbol; type; qty; avg; LTP or NAV label by type; mapped `benchmark`; hint “Wrong benchmark? Fix in Settings.”
3. `WindowSelect` on its own row.
4. Chips from `getWindowMetrics(holding.windows, window)`: Abs % / XIRR / CAGR / Outperf (`absolute_excess_pp`) via formatters; null → N/A.
5. `getHoldingSeries(id, window)` → `ReturnSeriesChart` with `holding_return` / `benchmark_return` (always absolute series; no Metric picker on detail).
6. Transactions table.

`apps/web/src/app/holdings/[id]/page.tsx`:

```tsx
import { HoldingDetailPage } from "@/components/HoldingDetailPage";

export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const instrumentId = Number(id);
  if (!Number.isFinite(instrumentId)) {
    return <p role="alert">Invalid holding</p>;
  }
  return <HoldingDetailPage instrumentId={instrumentId} />;
}
```

On 404 from API, show “Holding not found” + back link.

- [ ] **Step 4: Run tests**

Run: `cd apps/web && npm test -- src/__tests__/TransactionsTable.test.tsx`

Expected: PASS. Full `npm test` green.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/components/TransactionsTable.tsx apps/web/src/components/HoldingDetailPage.tsx \
  apps/web/src/app/holdings/\[id\]/page.tsx apps/web/src/__tests__/TransactionsTable.test.tsx
git commit -m "$(cat <<'EOF'
feat(web): add holding detail chart and transactions

EOF
)"
```

---

### Task 7: Import page (CSV, gap, report)

**Files:**
- Create: `apps/web/src/lib/import-report.ts`
- Create: `apps/web/src/components/CsvUpload.tsx`
- Create: `apps/web/src/components/ImportReport.tsx`
- Create: `apps/web/src/components/GapCallout.tsx`
- Create: `apps/web/src/components/ImportPage.tsx`
- Modify: `apps/web/src/app/import/page.tsx`
- Create: `apps/web/src/__tests__/ImportReport.test.tsx`

**Interfaces:**
- Consumes: `api.postImportCsv`, `api.getAlerts`
- Produces: session key `portfolio-tracker:last-import` storing last successful `ImportResult` JSON

Locked: single Console tradebook uploader (`postImportCsv`, not batch).

- [ ] **Step 1: Write failing tests**

```tsx
import { render, screen } from "@testing-library/react";
import { ImportReport } from "@/components/ImportReport";
import { GapCallout } from "@/components/GapCallout";

describe("ImportReport", () => {
  it("shows counts and flagged rows", () => {
    render(
      <ImportReport
        report={{
          format: "console_tradebook",
          new: 3,
          existing: 1,
          segment_counts: { equity: 2, mf: 2 },
          flagged_rows: ["row 4: missing price"],
          date_min: "2024-01-01",
          date_max: "2024-06-01",
          financial_years: ["2023-24"],
        }}
      />,
    );
    expect(screen.getByText(/3/)).toBeInTheDocument();
    expect(screen.getByText(/duplicates skipped|existing/i)).toBeInTheDocument();
    expect(screen.getByText(/row 4: missing price/)).toBeInTheDocument();
  });
});

describe("GapCallout", () => {
  it("exposes adjustable from/to defaults from alerts", () => {
    render(
      <GapCallout
        suggestedFrom="2024-01-01"
        suggestedTo="2024-06-01"
        message="Missing history"
      />,
    );
    expect(screen.getByDisplayValue("2024-01-01")).toBeInTheDocument();
    expect(screen.getByDisplayValue("2024-06-01")).toBeInTheDocument();
    expect(screen.getByText(/export that range/i)).toBeInTheDocument();
  });
});
```

Also unit-test `saveImportReport` / `loadImportReport` with a mock `sessionStorage` in `import-report` tests (can live in same file or `import-report.test.ts`).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/web && npm test -- src/__tests__/ImportReport.test.tsx`

Expected: FAIL.

- [ ] **Step 3: Implement Import UI**

`import-report.ts`:

```ts
import type { ImportResult } from "@/lib/api";

const KEY = "portfolio-tracker:last-import";

export function saveImportReport(report: ImportResult): void {
  if (typeof sessionStorage === "undefined") return;
  sessionStorage.setItem(KEY, JSON.stringify(report));
}

export function loadImportReport(): ImportResult | null {
  if (typeof sessionStorage === "undefined") return null;
  const raw = sessionStorage.getItem(KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as ImportResult;
  } catch {
    return null;
  }
}
```

Note: `ImportResult` is already exported from `api.ts` as `AppJson<"/import/csv","post">` — for single-file success shape use the non-batch branch (`format: "console_tradebook"`). If TypeScript unions with batch, narrow with `'format' in report`.

`CsvUpload` — `<input type="file" accept=".csv,text/csv" />` + Upload button; calls `onUpload(file)`.

`ImportPage`:
1. On mount: `getAlerts()`, `loadImportReport()`.
2. If `alerts.gap`, show `GapCallout` with editable date inputs (local state initialized from suggested).
3. On upload: `postImportCsv`; on success `saveImportReport` + set state; on error show API error text (and flagged section if present).
4. Show `ImportReport` for last result.

Copy: instruct user to export Console tradebook for the From–To range and upload here.

- [ ] **Step 4: Run tests**

Run: `cd apps/web && npm test -- src/__tests__/ImportReport.test.tsx`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/lib/import-report.ts apps/web/src/components/CsvUpload.tsx \
  apps/web/src/components/ImportReport.tsx apps/web/src/components/GapCallout.tsx \
  apps/web/src/components/ImportPage.tsx apps/web/src/app/import/page.tsx \
  apps/web/src/__tests__/ImportReport.test.tsx
git commit -m "$(cat <<'EOF'
feat(web): add Console CSV import with gap callout and report

EOF
)"
```

---

### Task 8: Settings (auth, sync, benchmarks) + OAuth callback

**Files:**
- Create: `apps/web/src/components/BenchmarkOverridesTable.tsx`
- Create: `apps/web/src/components/SettingsPage.tsx`
- Create: `apps/web/src/components/SettingsAuthPanel.tsx`
- Create: `apps/web/src/app/auth/callback/page.tsx`
- Modify: `apps/web/src/app/settings/page.tsx`
- Modify: `.env.example`
- Create: `apps/web/src/__tests__/SettingsAuth.test.tsx`

**Interfaces:**
- Consumes: auth + sync + benchmarks + catalogs APIs
- Produces: Settings §5.5 states; web OAuth completion route

- [ ] **Step 1: Write failing auth panel test**

```tsx
import { render, screen } from "@testing-library/react";
import { SettingsAuthPanel } from "@/components/SettingsAuthPanel";

describe("SettingsAuthPanel", () => {
  it("disables refresh when not logged in", () => {
    render(
      <SettingsAuthPanel
        connected={false}
        credentialsConfigured={true}
        lastSyncAt={null}
        onLogin={vi.fn()}
        onRefresh={vi.fn()}
        busy={false}
      />,
    );
    expect(screen.getByRole("button", { name: /log in with zerodha/i })).toBeEnabled();
    expect(
      screen.getByRole("button", { name: /refresh holdings \(log in first\)/i }),
    ).toBeDisabled();
  });

  it("enables refresh when logged in", () => {
    render(
      <SettingsAuthPanel
        connected={true}
        credentialsConfigured={true}
        lastSyncAt="2026-08-02T09:00:00+05:30"
        onLogin={vi.fn()}
        onRefresh={vi.fn()}
        busy={false}
      />,
    );
    expect(screen.getByRole("button", { name: /^refresh holdings$/i })).toBeEnabled();
    expect(screen.getByRole("button", { name: /log in again/i })).toBeEnabled();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/web && npm test -- src/__tests__/SettingsAuth.test.tsx`

Expected: FAIL.

- [ ] **Step 3: Implement Settings + callback**

`SettingsAuthPanel` — copy table from spec §5.5; primary/secondary buttons as specified.

`SettingsPage`:
1. Load `getAuthStatus`, `getBenchmarkSettings`, `getCatalogs`.
2. Auth panel: Login → `getLoginUrl()` then `window.location.href = login_url`.
3. Refresh → `postSync()` then reload status.
4. Doc blurb: “Kite api_key / api_secret live in `.env` (see `.env.example`); never entered here.”
5. If `!credentials_configured`, show warn to set env vars.
6. `BenchmarkOverridesTable`: columns Holding · Kind · Fund category · Compare to index.
   - Category `<select>` options from `catalogs.mf_categories`; when `needs_category`, highlight row / select placeholder “Choose category”.
   - Index `<select>` from `catalogs.benchmark_indexes`.
   - onChange → `putCategory` / `putBenchmark` then refresh list.

`apps/web/src/app/auth/callback/page.tsx` (client):

```tsx
"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

export default function AuthCallbackPage() {
  const params = useSearchParams();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = params.get("request_token");
    if (!token) {
      setError("Missing request_token");
      return;
    }
    void api
      .postCallback(token)
      .then(() => router.replace("/settings"))
      .catch((e: Error) => setError(e.message));
  }, [params, router]);

  if (error) return <p role="alert">{error}</p>;
  return <p>Completing Zerodha login…</p>;
}
```

Wrap with `<Suspense>` if Next requires it for `useSearchParams`.

Update `.env.example`:

```env
KITE_API_KEY=
KITE_API_SECRET=
# Prefer Next.js callback for the web UI:
KITE_REDIRECT_URL=http://localhost:3000/auth/callback
# API-only smoke alternative: http://127.0.0.1:8000/auth/callback
CORS_ORIGINS=http://localhost:3000
```

Do **not** commit real `.env`. Note in Settings UI that Kite console redirect must match.

- [ ] **Step 4: Run tests**

Run: `cd apps/web && npm test -- src/__tests__/SettingsAuth.test.tsx`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/components/BenchmarkOverridesTable.tsx apps/web/src/components/SettingsPage.tsx \
  apps/web/src/components/SettingsAuthPanel.tsx apps/web/src/app/settings/page.tsx \
  apps/web/src/app/auth/callback/page.tsx apps/web/src/__tests__/SettingsAuth.test.tsx \
  .env.example
git commit -m "$(cat <<'EOF'
feat(web): add Settings auth, sync, and benchmark overrides

EOF
)"
```

---

### Task 9: Glossary + final polish

**Files:**
- Create: `apps/web/src/lib/glossary.ts`
- Create: `apps/web/src/components/GlossaryTerm.tsx`
- Create: `apps/web/src/components/GlossaryPage.tsx`
- Modify: `apps/web/src/app/glossary/page.tsx`
- Create: `apps/web/src/__tests__/glossary.test.ts`

**Interfaces:**
- Consumes: none (static)
- Produces: jump chips + definitions for Absolute return, XIRR, CAGR, Outperformance (pp), Window, LTP, NAV, Benchmark / category index

- [ ] **Step 1: Write failing test**

```ts
import { describe, expect, it } from "vitest";
import { GLOSSARY_TERMS } from "@/lib/glossary";

describe("glossary", () => {
  it("includes required terms", () => {
    const ids = GLOSSARY_TERMS.map((t) => t.id);
    for (const need of [
      "absolute-return",
      "xirr",
      "cagr",
      "outperformance",
      "window",
      "ltp",
      "nav",
      "benchmark",
    ]) {
      expect(ids).toContain(need);
    }
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/web && npm test -- src/__tests__/glossary.test.ts`

Expected: FAIL.

- [ ] **Step 3: Implement Glossary**

`glossary.ts` — array of `{ id, title, body }` with plain-language short definitions (2–4 sentences each). Window body lists ITD / 1Y / 3Y / 5Y.

`GlossaryPage` — jump chips (`a href="#id"`) + `GlossaryTerm` blocks with matching `id` anchors. No charts, no Metric/Window chrome.

- [ ] **Step 4: Full verification**

```bash
cd apps/web && npm test && npm run build
```

Expected: all tests PASS; production build succeeds.

From repo root (optional): `npm test` (API + check:api + web).

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/lib/glossary.ts apps/web/src/components/GlossaryTerm.tsx \
  apps/web/src/components/GlossaryPage.tsx apps/web/src/app/glossary/page.tsx \
  apps/web/src/__tests__/glossary.test.ts
git commit -m "$(cat <<'EOF'
feat(web): add Glossary definitions page

EOF
)"
```

---

## Self-review

### 1. Spec coverage

| Spec section | Task |
| ------------ | ---- |
| §3 IA / routes | 1, 5–9 |
| §4 Shell dark + collapsible nav | 1 |
| §5.1 Overview stack | 4 (+ StatusBanner 3) |
| §5.2 Holdings two tables + Window | 5 |
| §5.3 Holding detail | 6 |
| §5.4 Import CSV + gap + report | 7 |
| §5.5 Settings auth/sync/benchmarks | 8 |
| §5.6 Glossary | 9 |
| §6 Components list | Tasks 1–9 |
| §7 Data flow / NEXT_PUBLIC_API_URL | uses existing `api.ts` |
| §8 Error/empty states | StatusBanner, N/A formatting, Settings disabled refresh, Import errors |
| §9 UI tests | each task |
| Chart Absolute-only limitation | Task 4 (documented in chart empty state) |
| Allocation Equity/MF/ETF | Task 2–4 client aggregate (API per-symbol unused for donut) |
| OAuth UX | Task 8 web callback + `.env.example` |

### 2. Placeholder scan

No TBD/TODO steps; concrete code, commands, and commit messages included.

### 3. Type consistency

- `WindowKey` / `MetricKey` defined in Task 2; used in Tasks 3–6
- Outperf holdings column = `absolute_excess_pp` (Task 5 decision)
- Import storage key `portfolio-tracker:last-import`
- Chart series field names `portfolio_return` / `benchmark_return` / `holding_return` match OpenAPI

### Gaps intentionally deferred

- Playwright smoke (spec: optional later)
- XIRR/CAGR chart series (blocked on API; UI shows N/A)
- Changing live `.env` redirect (engineer updates local `.env` to match `.env.example` when using web OAuth)
