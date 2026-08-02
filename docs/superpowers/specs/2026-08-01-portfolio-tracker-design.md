# Portfolio Tracker — Design Spec

**Date:** 2026-08-01  
**Status:** Approved for planning  
**Product:** Local, open-source, BYO-Zerodha personal portfolio tracker

## 1. Goal

A self-hosted portfolio tracker for Zerodha equity and Coin mutual funds. Clone the repo, add your own Kite Connect credentials, import trade history, and see holdings, absolute returns, XIRR, CAGR, and outperformance vs category-appropriate benchmarks — with a proper analytics UI.

Anyone who clones the repo runs their own local instance against their own Zerodha account and local database. No shared cloud multi-tenancy in v1.

## 2. Scope

### In scope (v1)

- Local monorepo: **Next.js (web) + FastAPI (api) + SQLite**
- **Kite Connect Personal (free)** for holdings sync and same-day trade append
- **Console CSV import** for full history (equity tradebook **and** Coin/MF tradebook); re-import for gap backfill
- Asset types: **equity delivery, ETFs, Coin mutual funds**
- Metrics (portfolio + per instrument) for **ITD** and trailing **1Y / 3Y / 5Y** when history allows:
  - Absolute return (₹ and %)
  - CAGR when span ≥ 365 days (else N/A)
  - XIRR (cashflow-based; buys/sells/SIPs + terminal MV; **no dividends**)
  - Benchmark return and **excess / outperformance** (percentage points) for absolute, XIRR, and CAGR when both sides exist
- Benchmark mapping by MF category (auto from AMFI/scheme metadata when possible; e.g. flexi cap → Nifty 500, mid cap → Nifty Midcap 150, small cap → Nifty Smallcap 250); stocks/ETFs default to **Nifty 500**; all overridable in Settings
- Portfolio-level outperformance: **value-weighted blend** of each holding’s benchmark
- Gap detection and holdings-vs-transactions reconcile with CSV backfill prompts
- Market data via **Yahoo Finance** (stocks/ETFs/indices) + **AMFI** (mutual fund NAVs); Kite Personal has no market data
- GitHub-ready: `.env.example`, README setup, secrets never committed

### Out of scope (v1)

- Hosted multi-user SaaS
- EPF, FD, RD, PAASA, Bank Accounts, Cash / other brokers (later)
- F&O / intraday as first-class long-term portfolio metrics
- Free custom date-range picker (v1 uses fixed ITD + 1Y/3Y/5Y only; not arbitrary ranges)
- Dividend cashflows in XIRR / absolute return; corporate-action reconstruction beyond relying on Zerodha qty/avg
- Projections, expected corpus, churn / rebalancing analysis (**v1.1**)
- Console scraping / unofficial automation of CSV download
- Paid Kite Connect market-data dependency (optional later enhancement)
- Real Zerodha credentials in CI

### v1.1 (explicitly deferred)

- Forward projections / expected returns over N years
- Churn / reallocation analysis
- Non-Zerodha instruments and additional broker adapters
- Optional paid Kite Connect for native live/historical candles
- Optional free custom return windows / YTD control; optional dividend-aware XIRR

## 3. Architecture

```
┌─────────────────┐     HTTP      ┌──────────────────┐
│  Next.js (web)  │ ────────────► │  FastAPI (api)   │
│  dashboard UI   │               │  Kite + metrics  │
└─────────────────┘               └────────┬─────────┘
                                           │
              ┌──────────────┬─────────────┼─────────────┬──────────────┐
              ▼              ▼             ▼             ▼              ▼
         SQLite DB    Kite Personal   Console CSV   Yahoo Finance     AMFI
         (local)      (holdings +     (tradebook    (stocks/ETFs/   (MF NAVs)
                       today trades)   history)      indices)
```

- **web:** Overview, Holdings, Performance, Import, Settings
- **api:** auth, sync, import, portfolio queries, metrics, prices
- **db:** SQLite file under `data/` (gitignored)
- **config:** `.env` with Kite `api_key` / `api_secret`; never commit secrets
- **prices:** `PriceProvider` abstraction; v1 implementations = Yahoo Finance + AMFI (swappable later for paid Kite market data)

Portable personal app: one clone = one local user = one SQLite file. Credentials are always the cloner’s own Kite Connect Personal app.

Auth clarification: the app does **not** store Zerodha passwords. Flow is Kite OAuth (`api_key` / `api_secret` → browser login → `access_token`, typically re-login after ~6 AM IST expiry).

## 4. Components

### API modules

| Module       | Responsibility                                                           |
| ------------ | ------------------------------------------------------------------------ |
| `kite_auth`  | Login URL, token exchange, local token persistence, expiry handling      |
| `kite_sync`  | Holdings (equity + MF), append today’s trades                            |
| `csv_import` | Parse Console equity + Coin/MF tradebooks (detect by headers); idempotent upserts |
| `portfolio`  | Allocation, value, unrealized P&L                                        |
| `metrics`    | Absolute, CAGR, XIRR, benchmark excess (instrument + portfolio)          |
| `benchmarks` | Category → index defaults, overrides, value-weighted portfolio benchmark |
| `prices`     | Yahoo Finance (equity/ETF/index) + AMFI (MF NAV); cache in DB            |
| `reconcile`  | Gap detection, holdings vs transaction-implied qty                       |

### Web pages

| Page        | Content                                                                                  |
| ----------- | ---------------------------------------------------------------------------------------- |
| Overview    | Total value, P&L, allocation, ITD metrics + available 1Y/3Y/5Y summaries, gap/reconcile banners |
| Holdings    | Per-row qty, avg, LTP, value, absolute %, XIRR, CAGR, excess vs benchmark (Δ pp)         |
| Performance | Window switcher (ITD / 1Y / 3Y / 5Y); portfolio vs blend; contributor excess; charts     |
| Import      | Console Equity and/or MF tradebook CSV; gap range prompts; segment/flagged import report |
| Settings    | Connect Zerodha, Sync now, MF category + benchmark overrides, setup hints (no secrets)   |

## 5. Data model (SQLite)

| Table               | Purpose                                                          |
| ------------------- | ---------------------------------------------------------------- |
| `settings`          | Local token blob, last sync / last trade append timestamps       |
| `instruments`       | Symbol, ISIN, type (equity/etf/mf), exchange, MF category        |
| `transactions`      | Date, side, qty, price, fees, source (`csv` / `api`), dedupe key |
| `holdings_snapshot` | Qty, avg_price, as_of from API                                   |
| `prices`            | Symbol, date, close/ltp                                          |
| `benchmark_map`     | Instrument → benchmark index (default or override)               |
| `benchmark_prices`  | Index series for excess calculation                              |
| ~~`metrics_cache`~~ | **Deferred to v2** — v1 recomputes metrics on every read         |

### Returns windows (v1)

Compute absolute, CAGR, XIRR, and excess for:

| Window | Definition |
| ------ | ---------- |
| **ITD** | First cashflow / first trade in scope → as-of |
| **1Y / 3Y / 5Y** | Trailing windows ending at as-of (`as_of − 365/1095/1825` days). If inception is after the window start → that window is N/A |

No free custom date-range picker in v1. Rolling absolute prefers point-to-point on opening MV → terminal MV; rolling XIRR uses opening MV as a synthetic cashflow plus in-window trades plus terminal MV.

### XIRR cashflow rule

- Buys / SIPs → negative cashflows on trade dates
- Sells → positive cashflows on trade dates
- Current market value → terminal positive cashflow on as-of date
- **Dividends ignored** in v1 (not modeled as cashflows). Stock splits / corporate actions: rely on Zerodha holdings qty/avg and Console trade history as recorded; no separate corporate-action engine.

### CAGR rule

- Compute CAGR only when the span from first cashflow (or first trade) to as-of is **≥ 365 days**.
- Shorter spans → show N/A (avoid noisy annualization).

### Absolute return

- **Invested cost** = net cash deployed for that scope: sum of buy notional (include fees in cost when present in CSV) minus cost removed on sells (proportional avg-cost). Portfolio invested cost = sum across instruments (or equivalent portfolio cashflows excluding the terminal MV cashflow).
- ₹ gain: `current_value − invested_cost`
- %: `(current_value − invested_cost) / invested_cost` when invested_cost > 0; otherwise N/A

### MF category resolution

1. On instrument create/update: resolve category from **AMFI / scheme metadata** (ISIN or scheme code) when available.
2. If unknown → default category mapping uses Nifty 500 and UI shows **set-category** flag.
3. User override in Settings wins for both category and benchmark index.

### Benchmark defaults

| Holding type / MF category | Default index                       |
| -------------------------- | ----------------------------------- |
| Flexi cap                  | Nifty 500                           |
| Large cap                  | Nifty 100                           |
| Mid cap                    | Nifty Midcap 150                    |
| Small cap                  | Nifty Smallcap 250                  |
| Unknown MF category        | Nifty 500 + UI flag to set category |
| Stocks / unknown ETFs      | Nifty 500                           |
| Index ETF                  | Underlying index when known         |

All mappings overridable in Settings.

### Portfolio excess

Value-weighted blend: each holding’s benchmark **point-to-point** return weighted by current market value weight for absolute excess; portfolio CAGR excess uses a value-weighted blend of per-instrument benchmark CAGRs. **XIRR excess** uses a same-cashflow **benchmark XIRR** (invest identical ₹/dates into each holding’s mapped index; terminal = remaining index MV) — never compare XIRR to a raw point-to-point bench %. Instrument excess shown separately for every stock and MF. Expose excess for absolute, XIRR, and CAGR when both sides exist.

### Market data providers (v1)

Kite Connect Personal does **not** provide LTP or historical candles. All marks-to-market and benchmark series come from:

| Asset                                                      | Provider                                                                             | Notes                                                                           |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------- |
| Stocks / ETFs                                              | **Yahoo Finance** (e.g. `yfinance`, symbols like `RELIANCE.NS`)                      | LTP + history; cached in `prices`                                               |
| Benchmark indices (Nifty 500, Midcap 150, Smallcap 250, …) | **Yahoo Finance** (mapped index tickers)                                             | Cached in `benchmark_prices`; if a ticker is missing, document fallback mapping |
| Mutual funds                                               | **AMFI** daily NAV (direct files and/or a thin AMFI-compatible API such as mfapi.in) | Match by ISIN / scheme code from Coin; NAV usually T+1                          |

Refresh on sync / app open. Failures leave holdings visible without LTP and mark metrics incomplete (see §7). Google Finance is **not** used (no suitable backend API). Optional v1.1+: paid Kite Connect as an alternate equity/index provider behind the same `PriceProvider` interface; MF NAVs remain AMFI.

## 6. Data flow

### First run

1. Clone → `.env.example` → `.env` (Kite keys + local redirect URL)
2. Start api + web
3. Settings → Connect Zerodha → OAuth → store access token
4. Import Console equity tradebook and/or Coin MF tradebook CSV(s) → `transactions` (importer detects format by headers)
5. Sync → holdings snapshot + today’s trades (if any)
6. Price job → Yahoo Finance for equity/ETF/index marks; AMFI for MF NAVs
7. UI reads holdings; metrics (absolute / CAGR / XIRR / excess) **recomputed on read** (no `metrics_cache` in v1)

### Ongoing

- On Sync / app open (valid token): refresh holdings; append **today’s** API trades; run gap check; reconcile; refresh prices; metrics recompute on next read
- Token expired → reconnect banner; sync blocked until OAuth
- After missed trading days: gap warning with suggested Console date range; user imports CSV; idempotent merge
- If API holdings ≠ transaction-implied positions → reconcile alert; prefer resolving via CSV before trusting XIRR (user may dismiss with acknowledgment)

### Source of truth

| Data                    | Source                                                    |
| ----------------------- | --------------------------------------------------------- |
| Historical trades       | Console CSV (+ API only for days the app actually synced) |
| Current qty / avg       | Kite holdings snapshot                                    |
| Equity/ETF/index prices | Yahoo Finance (cached)                                    |
| MF NAVs                 | AMFI (cached)                                             |
| Returns                 | Transactions + prices/NAVs + terminal MV                  |
| Benchmarks              | Category map + Yahoo index history                        |

**CSV import:** Support both Console **equity tradebook** and **Coin/MF tradebook** exports on one Import page. Detect format from headers/columns; reject unknown shapes with a clear error. No official full-history download API; v1 does **not** scrape Console. Pattern is manual full history once (one or both CSVs), API append when the app runs, CSV backfill for gaps.

## 7. Error handling

| Situation                        | Behavior                                               |
| -------------------------------- | ------------------------------------------------------ |
| Missing/invalid Kite credentials | Setup guidance; sync disabled                          |
| Access token expired             | Reconnect banner; sync blocked                         |
| Kite rate limit / downtime       | Backoff retry; show last error + last success time     |
| CSV parse failure                | All-or-nothing import in v1; clear error report        |
| Duplicate trades                 | Idempotent skip; counts of new vs existing             |
| Trade-append gaps                | Warning + suggested Console export range               |
| Holdings ≠ transactions          | Per-symbol diff; reconcile before trusting metrics     |
| Price/benchmark fetch fail       | Holdings without LTP; metrics marked incomplete; retry |
| Unknown MF category              | Default Nifty 500 + set-category flag                  |
| Empty state                      | CTA: Connect → Import → Sync                           |

No secrets in logs or API responses.

## 8. Testing

### API

- Unit: CSV fixtures, absolute/CAGR/XIRR, excess, category → benchmark map
- Unit: idempotent merge, gap detection, reconcile
- Unit: price providers mocked (Yahoo + AMFI fixtures); symbol/ISIN mapping
- Integration: mocked Kite client → sync/import → DB → metrics endpoints

### Web

- Component tests: metric cards, holdings table, gap/reconcile/token banners
- Optional later: Playwright smoke with mocked API

### Manual (README)

- Fresh clone → env → OAuth → CSV → sync → numbers roughly match Console
- Re-import same CSV → zero duplicates
- Expired token → reconnect path

CI must not use real Zerodha keys.

## 9. Repository layout (target)

```
portfolio-tracker/
  apps/web/          # Next.js
  apps/api/          # FastAPI
  data/              # SQLite (gitignored)
  docs/superpowers/specs/
  .env.example
  README.md
```

Exact package manager / tooling chosen at implementation-plan time; design assumes npm/pnpm for web and uv/poetry/pip for api.

## 10. Success criteria (v1)

- New user can clone, configure Kite Personal keys, connect, import equity and/or Coin tradebook CSVs, and see equity + MF portfolio locally
- Overview shows total value plus absolute / XIRR / CAGR / outperformance for ITD, with trailing 1Y/3Y/5Y when history allows; Performance page switches windows
- Equity/ETF marks from Yahoo Finance; MF marks from AMFI NAVs
- Each stock and MF shows its own returns and excess vs its mapped index (category from AMFI when possible, overridable)
- Missing days without app use are detected; CSV backfill restores history without duplicates
- No credentials or portfolio data committed to git

## 11. Locked v1 product decisions

| Topic | Decision |
| ----- | -------- |
| Returns windows | ITD + trailing 1Y/3Y/5Y when history allows; no free custom date picker |
| Dividends / corporate actions | Dividends excluded from XIRR; no corporate-action engine; trust Zerodha qty/avg + trade CSVs |
| CAGR eligibility | Span ≥ 365 days, else N/A |
| Excess units | Absolute vs point-to-point bench %; CAGR vs bench CAGR; XIRR vs same-cashflow benchmark XIRR |
| Metrics cache | v2 only; v1 recomputes on read |
| CSV shapes | Both Console equity tradebook and Coin/MF tradebook; header-based detection; one Import page |
| MF category | Auto from AMFI/scheme metadata when possible; Settings override; unknown → Nifty 500 + flag |

## 12. Non-goals reminder

Hosting, multi-user accounts, non-Zerodha assets, F&O-first analytics, projections, and churn analysis are deferred. Architecture should not block adding broker adapters or Python-heavy projection modules in v1.1.
