# Portfolio Tracker — UI Design Spec

**Date:** 2026-08-02  
**Status:** Approved for planning  
**Product:** Local Zerodha equity + Coin MF portfolio tracker (Next.js web)  
**Companion:** Wireframe HTML under `.superpowers/brainstorm/` (gitignored; not committed)

This spec defines the **web UI information architecture, page layouts, copy, and interaction model**. Metric formulas, API contracts, and data providers remain as in `2026-08-01-portfolio-tracker-design.md` unless this document explicitly narrows UI scope.

## 1. Goal

Ship a dark, balanced analytics UI so a single local user can:

1. See total portfolio value and absolute return on landing
2. Inspect portfolio return / outperformance vs market-weighted category benchmarks
3. Browse holdings (stocks/ETFs and mutual funds) with Abs %, XIRR, CAGR, outperformance
4. Drill into one holding for chart + transactions
5. Import Console tradebook CSVs and refresh Zerodha holdings
6. Override benchmarks and read plain-language definitions in Glossary

## 2. Scope

### In scope (v1 UI)

- Dark theme app shell with **collapsible left nav**
- Pages: **Overview · Holdings · Import · Settings · Glossary**
- Hidden route: **holding detail** (`/holdings/[id]`) — row drilldown only, not in nav
- Charts on **Overview** and **holding detail** only (axes + hover tooltips)
- Per-block / per-table **Window** controls (ITD / 1Y / 3Y / 5Y) where return % are shown
- Overview portfolio return cards: local **Metric** (Absolute / XIRR / CAGR) + **Window**
- Plain-language labels; Glossary owns definitions (no dense ⓘ tooltips on every metric)
- Inline status (outdated holdings, import gaps) — not global toast spam
- Kite **api_key / api_secret** via `.env` only; Settings = login + refresh + benchmark overrides

### Out of scope (v1 UI)

- Churn / “move this money” recommendations
- Separate Performance item in left nav
- Separate Coin vs Console upload buttons (one Console tradebook uploader)
- Global shell-level Metric/Window applying to the whole app
- Light theme / system theme (dark only for v1)
- Entering Kite secrets in the browser
- Expanding SEBI category / index catalogs beyond the v1 shortlist (lists must remain data-driven for later)

## 3. Information architecture

```
┌──────────────────┐
│ Collapsible nav  │
│ Overview         │──► landing: value, returns, chart, allocation
│ Holdings         │──► two tables; row click ──► Holding detail (hidden)
│ Import           │──► one Console CSV upload + gap / report
│ Settings         │──► login, refresh holdings, benchmark overrides
│ Glossary         │──► term definitions
└──────────────────┘
```

| Route (indicative) | Nav | Purpose |
| ------------------ | --- | ------- |
| `/` | Overview | Portfolio pulse |
| `/holdings` | Holdings | Tables only |
| `/holdings/[id]` | (none; Holdings highlighted) | Chart + transactions |
| `/import` | Import | CSV + gaps |
| `/settings` | Settings | Auth, sync, benchmarks |
| `/glossary` | Glossary | Definitions |

## 4. Shell & visual direction

- **Theme:** Dark (navy/charcoal surfaces, muted borders, green for positive, amber for warnings)
- **Nav:** Left rail; collapse to icons; brand “Portfolio Tracker” at top
- **Density:** Balanced — hero metrics with breathing room; tables scannable, not spreadsheet-dense
- **Charts:** Labeled X/Y axes; hover shows date + series values; library chosen at implementation (e.g. Recharts)
- **Copy:** Prefer “Log in with Zerodha”, “Refresh holdings”, “Outperformance” over jargon-only labels

### What Window / Metric affect

| Always “as of today” | Scoped by Window (and Metric where present) |
| -------------------- | --------------------------------------------- |
| Total / position market value | Absolute %, XIRR, CAGR |
| Invested cost, unrealized P&L ₹ | Outperformance (pp) |
| Allocation weights | Return charts |

## 5. Pages

### 5.1 Overview (landing) — frozen

**Stack (top → bottom):**

1. Inline status when needed: e.g. “Holdings may be outdated” + **Refresh holdings** (same action as Settings; disabled if not logged in). Link to Import when the issue is a history gap.
2. **Total portfolio value** + invested cost; **Absolute return** as +₹ and +% (ITD story on the hero).
3. Two cards with **local** Metric + Window dropdowns each:
   - **Portfolio return** (default Metric: XIRR)
   - **Outperformance** — “you beat category benchmarks by X pp”; market-weighted by holding value. Show short breakdown when helpful (portfolio % − benchmark %).
4. **Portfolio vs category benchmarks** line chart with its own Metric + Window; axes + hover.
5. **Asset allocation** donut/pie (Equity / Mutual funds / ETFs) — as-of today, no Window.

**Labeling:** Prefer “Outperformance” / “category benchmarks (market-weighted)” over “excess” / “blend” in primary UI.

### 5.2 Holdings — frozen

- Page-level **Window** dropdown (applies to return columns in both tables).
- **No graph** on this page.
- **No Metric picker** — columns are Abs % · XIRR · CAGR · Outperf. (pp).
- **Two tables:**
  1. Stocks & ETFs (LTP column)
  2. Mutual funds (NAV column; show category)
- Row click → holding detail.
- No churn section; no per-cell ⓘ.

### 5.3 Holding detail (drilldown) — frozen

Reached only from Holdings. Layout:

1. ← Back to Holdings  
2. Identity header (symbol/scheme, type, qty, avg, LTP or NAV, mapped benchmark). Hint: wrong benchmark → Settings.  
3. **Window** on its **own row** under the name.  
4. Returns chips row: Abs % · XIRR · CAGR · Outperf.  
5. Chart: holding vs mapped category benchmark (axes + hover); follows Window.  
6. **Transactions** table: date, side, qty, price, amount, source (CSV / API).

Benchmark edit is **not** on this page.

### 5.4 Import — frozen

- Single control: upload **Console tradebook CSV** (all Console exports; header-based detection for equity / MF shapes).
- Gap callout with suggested **From / To** dates (user-adjustable) and instruction to export that range and upload.
- Last import report: counts, duplicates skipped, flagged rows / errors highlighted on-page.
- Reconcile / incomplete history messaging lives here (and may deep-link from Overview status), not as a global toast.

### 5.5 Settings — frozen

**Before you start:** Document that Kite key/secret live in `.env` (from `.env.example`); never entered in the UI.

**Your Zerodha account**

| State | Status copy | Primary action | Secondary |
| ----- | ----------- | -------------- | --------- |
| Not logged in | Not logged in — log in once so we can load your holdings | **Log in with Zerodha** (browser OAuth) | **Refresh holdings (log in first)** — disabled |
| Logged in | Logged in · holdings last refreshed … | **Log in again** | **Refresh holdings** |

Refresh holdings = sync holdings, append today’s trades, refresh prices. Missing history days → Import.

**Compare each holding to which index?**  
Table: Holding · Kind · Fund category · Compare to index.  
Unknown MF category: **Choose category** highlighted until set.

**v1 dropdown shortlists** (data-driven; expandable later without UI redesign):

| Control | Values |
| ------- | ------ |
| Fund category | Flexi Cap, Large Cap, Mid Cap, Small Cap |
| Compare to index | Nifty 500, Nifty 100, Nifty Midcap 150, Nifty Smallcap 250, Nifty 50 |

Defaults match API `DEFAULT_BY_CATEGORY` / stock→Nifty 500 (see product design + `benchmarks.py`).

### 5.6 Glossary — frozen

Static page with jump chips and short definitions for at least:

- Absolute return  
- XIRR  
- CAGR  
- Outperformance (pp)  
- Window (ITD, 1Y, 3Y, 5Y)  
- LTP and NAV  
- Benchmark / category index  

No charts. No Metric/Window chrome.

## 6. Components (web)

Logical building blocks (names indicative):

| Component | Role |
| --------- | ---- |
| `AppShell` | Collapsible nav + main |
| `StatusBanner` | Inline outdated / gap / login-needed |
| `MetricWindowSelects` | Pair of dropdowns (Overview cards / chart) |
| `WindowSelect` | Single window (Holdings, detail) |
| `ValueHero` | Portfolio value + absolute return |
| `AllocationChart` | Donut/pie |
| `ReturnSeriesChart` | Line chart with axes + tooltip |
| `HoldingsTable` | Stocks/ETFs or MF variant |
| `TransactionsTable` | Holding detail |
| `CsvUpload` | Single Console uploader |
| `ImportReport` | Last import + flags |
| `BenchmarkOverridesTable` | Settings |
| `GlossaryTerm` | Definition block |

Prefer small focused modules over one mega-dashboard file.

## 7. Data flow (UI)

```
Browser (Next.js)
  ├─ Overview / Holdings / Detail ──GET──► portfolio + metrics APIs
  ├─ Import ──POST──► CSV import; GET gap / reconcile status
  ├─ Settings ──GET/POST──► auth login URL / token status; sync; benchmark/category PUT
  └─ Glossary ── static content (no API)
```

- Browser talks to API via `NEXT_PUBLIC_API_URL` (existing client).
- Metrics recomputed on read (no UI cache inventing numbers).
- N/A windows/metrics render as N/A, not zero.

## 8. Error & empty states

| Situation | UI |
| --------- | -- |
| Not logged in | Settings primary CTA; Refresh disabled; Overview may prompt login |
| Token expired | Same as not logged in + “Log in again” |
| Stale holdings / prices | Inline “Holdings may be outdated” + Refresh holdings |
| History gap | Import gap callout with date range; optional Overview link to Import |
| Bad CSV / flagged rows | Import report error section |
| Missing LTP/NAV | Show holding; metrics incomplete / N/A as API indicates |
| Unknown MF category | Flag in Settings table; outperf still uses default index until fixed |

## 9. Testing (UI)

- Unit/component: shell nav, Window/Metric controls update displayed values, tables render N/A, status banner actions
- Import: upload success + error report rendering (mocked API)
- Settings: logged-in vs logged-out button states; disabled refresh
- Glossary: sections/anchors render
- Optional later: Playwright smoke with mocked API

No real Zerodha credentials in CI.

## 10. Relationship to product design

| Product design (2026-08-01) | UI design (this doc) |
| --------------------------- | -------------------- |
| Pages include Performance | Performance folded into Overview + holding detail; no Performance nav item |
| Global-ish window switching | Window (and Metric on Overview cards) are local to the control surface |
| Coin + Console upload callouts | One Console tradebook uploader; header detection may still accept MF-shaped Console CSVs |
| Tooltips for metrics | Glossary page; avoid dense ⓘ everywhere |
| Churn deferred | Explicitly out of UI |

## 11. Locked UI decisions

| Topic | Decision |
| ----- | -------- |
| Nav | Collapsible left; 5 items + hidden holding detail |
| Theme | Dark v1 |
| Overview hero | Value + ITD absolute ₹/% |
| Overview return cards | Local Metric + Window; default Metric XIRR |
| Outperformance wording | Prefer “Outperformance” + market-weighted category benchmarks |
| Holdings layout | Two tables; Window at top; all return columns; no chart |
| Drilldown | Chart + transactions; Window on own row under name |
| Benchmark fix | Settings only |
| Credentials | `.env` only |
| Category/index lists | v1 shortlist; data-driven for future expansion |
| Charts | Overview + detail; axes + hover |

## 12. Success criteria (UI v1)

- User opens Overview and understands value, absolute return, portfolio return, and outperformance without reading the product design doc
- Holdings split stocks/ETFs vs MFs; drilldown shows chart and transactions
- Import is one obvious upload path with gap dates and a clear report
- Settings makes login / refresh / benchmark fix obvious in plain language
- Glossary defines XIRR, CAGR, absolute return, windows, LTP/NAV, outperformance, benchmarks
- Wireframes used for alignment are not required in the git repo

## 13. Next step

Implementation plan via writing-plans skill (routes, components, chart library, API wiring, tests) — after engineer review of this spec.
