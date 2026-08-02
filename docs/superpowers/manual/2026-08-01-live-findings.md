# Live API findings — 2026-08-01

## Environment
- Date / time (IST): 2026-08-01 ~19:25 IST (first pass); ~19:40 IST (second pass after fixes)
- API commit SHA: first pass `0914dfd`; post-fix tip `9acddf6`
- Market open?: no (Saturday)
- Equity CSV slices imported (basenames only): `tradebook-RYY010-EQ (2).csv`, `tradebook-RYY010-EQ (1).csv`, `tradebook-RYY010-EQ.csv`
- MF CSV slices imported (basenames only): `tradebook-RYY010-MF.csv`, `tradebook-RYY010-MF (1).csv`, `tradebook-RYY010-MF (2).csv`
- Console total value (approx): not captured; post-fix API `total_value` ≈ **22.72L INR**
- Known CSV coverage end (EQ / MF): EQ 2026-01-22 / MF 2026-03-05

## Checklist result
- [x] Health
- [x] Auth (login → callback → status)
- [x] Equity + MF multi-file import (one request, FY slices)
- [x] Wrong-input file rejected with re-import `action` (good files kept)
- [x] Re-import idempotent (`new=0`)
- [x] Sync + prices *(post-fix: AMFI rows > 0; remaining fails = SGB/delisted/DVR)*
- [x] Overview / holdings / alerts / performance *(post-fix numbers sane)*
- [x] Gap/reconcile alerts explained by post-CSV history gap (or filed as bug)
- [x] Settings override round-trip
- [x] Logout → sync 401 *(first pass)*

## Import / sync snapshot (scrubbed)

### First pass (pre-fix)
- Multi-file: `accepted=6`, `rejected=0`, `new=1099`
- Sync: AMFI price rows **0**; `total_value≈85k` (GOLDIETF-dominated); MF `ltp` null
- Kite MF instruments duplicated as `symbol=ISIN`

### Second pass (post F1/F2/AMFI ISIN + aliases)
- Sync: `holdings_count=14`, `prices.updated≈34k` incremental, **`amfi_fails=0`**, `amfi` price rows **33722**
- `total_value≈22,71,770`, ITD `xirr≈0.244` (fraction), absolute gain ≈ +6.78L on invested ≈15.94L
- Windows: `ITD` + `3Y` present; `1Y`/`5Y` null
- Positive qty with LTP missing: SGB×3, `IDFC`, `TRIL` only
- Yahoo aliases cleared ZOMATO/HBLPOWER/SWANENERGY from failed list
- Remaining Yahoo fails: `TATAMTRDVR`, `TATAMOTORS`, `IDFC`, `TRIL`, SGB\* (P3 / unsupported)
- Snapshot MF rows merge onto named CSV instruments (F2); 3 kite-only ISINs remain as symbol=ISIN (`INF846K013Y8`, `INF179KB1HP9`, `INF109K013N3`) — not in imported tradebook names
- Reconcile length 24 (CSV history gap + residual identity/noise) — expected until fresh ≤365-day export

## Bugs
| ID | Severity | Endpoint / area | Observed | Expected | Repro | Status |
|----|----------|-----------------|----------|----------|-------|--------|
| F1 | P0 | AMFI refresh | 0 AMFI rows; silent MF miss | NAVs + failed list | `/sync` after MF import | **Fixed** (`33018a5` report empty; `9acddf6` ISIN→scheme via `/mf` list) |
| F2 | P0 | Kite MF identity | Duplicate INF\* instruments | Merge by ISIN onto CSV name | import MF + `/sync` | **Fixed** (`90d042e`) |
| F3 | P1 | Yahoo renames | ZOMATO/HBLPOWER/SWANENERGY failed | Alias map | `/sync` | **Fixed** (`33018a5`); TATAMOTORS/DVR/IDFC/TRIL/SGB remain |
| F4 | — | contributors sort | Not by weight | By `absolute_excess_pp` | n/a | Not a bug |
| F5 | P2 | Misleading metrics when unpriced | ITD xirr ≈ -90% pre-fix | Re-check after prices | first pass | **Cleared** by F1/F2 |
| F6 | P2 | Dust MF qty | `5.68e-14` | Flat zero | holdings | **Fixed** (`abab538`) |
| F7 | P3 | `live_smoke.sh` bash 3.2 | `[-1]` subscript | Compatible index | script | **Fixed** (`268fb1c`) |
| F8 | P3 | CSV coverage / reconcile | 24 reconcile diffs; EQ/MF end before today | Expected data gap | n/a | Document only |

## Triage
- Fix plan: `docs/superpowers/plans/archive/2026-08-01-api-live-fixes.md`
- Residual open (non-blocking for frontend): Yahoo gaps for delisted/DVR/demerger + SGB unsupported; kite-only MF display names; optional fresh CSV slices for tighter reconcile

## Verdict
- **API ready for Task 12 frontend** after live re-verification on `9acddf6`.
- Multi-file import, GET OAuth callback, performance route, AMFI NAVs, and MF identity merge verified live.

## Notes
- Console max export window: 365 days; EQ and MF exported separately; users typically import by Indian FY
- GET `/auth/callback` worked for browser OAuth (`connected=true`)
- mfapi `/mf/search?q=<ISIN>` returns `[]` — must resolve via `/mf` scheme list `isinGrowth` / `isinDivReinvestment`
- Optional follow-up data: export EQ 2026-01-23→today and MF 2026-03-06→today for tighter reconcile
