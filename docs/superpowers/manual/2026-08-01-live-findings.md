# Live API findings — 2026-08-01

## Environment
- Date / time (IST): 2026-08-01 ~19:25 IST
- API commit SHA: `0914dfd` (smoke) / branch tip after script fix `268fb1c`
- Market open?: no (Saturday)
- Equity CSV slices imported (basenames only): `tradebook-RYY010-EQ (2).csv`, `tradebook-RYY010-EQ (1).csv`, `tradebook-RYY010-EQ.csv`
- MF CSV slices imported (basenames only): `tradebook-RYY010-MF.csv`, `tradebook-RYY010-MF (1).csv`, `tradebook-RYY010-MF (2).csv`
- Console total value (approx): not captured this run (API `total_value` ≈ 84.8k INR — **not trustworthy**; see F1/F2)
- Known CSV coverage end (EQ / MF): EQ 2026-01-22 / MF 2026-03-05

## Checklist result
- [x] Health
- [x] Auth (login → callback → status)
- [x] Equity + MF multi-file import (one request, FY slices)
- [x] Wrong-input file rejected with re-import `action` (good files kept)
- [x] Re-import idempotent (`new=0`)
- [x] Sync + prices *(sync HTTP 200; prices incomplete — see bugs)*
- [x] Overview / holdings / alerts / performance *(endpoints respond; numbers wrong — see bugs)*
- [x] Gap/reconcile alerts explained by post-CSV history gap (or filed as bug) *(reconcile partly expected; also amplified by F2)*
- [x] Settings override round-trip
- [x] Logout → sync 401

## Import / sync snapshot (scrubbed)
- Multi-file: `accepted=6`, `rejected=0`, `new=1099`, `existing=12`; FY labels correct per file
- Wrong-input batch: `accepted=1`, `rejected=1`, rejected `code=csv_format`, `action` contains re-import guidance
- Single bad `file=`: HTTP 400 with same `action`
- Idempotent re-import: `new=0`, `existing=98`
- Sync: `holdings_count=14`, `trades_appended=0` (weekend OK), `prices.updated≈211k` (Yahoo history), `prices.failed` = 10 equities/SGB, `incomplete=true`
- AMFI price rows in DB after sync: **0**
- Auth after sync: `connected=true`, `last_sync_at` set
- Overview: `total_value≈84758`, `incomplete=true`, `invested_cost≈1.59M`, ITD `xirr≈-0.90` (fraction OK; magnitude nonsense while MFs unpriced)
- Holdings HTTP: 146 instruments; 29 with `qty>0`; only 3 with non-null `value` (GOLDIETF + 2 tiny equities)
- Alerts: `gap=null`; `reconcile` length 32
- Performance: `default_window=ITD`; contributors weights sum ≈ 1.0; **not sorted by weight**
- Windows: only `ITD` available (`1Y`/`3Y`/`5Y` null)
- Settings: PUT benchmark/category → `source=user`
- Logout → sync HTTP 401, detail mentions reconnect

## Bugs
| ID | Severity | Endpoint / area | Observed | Expected | Repro |
|----|----------|-----------------|----------|----------|-------|
| F1 | P0 | `POST /sync` prices / AMFI | After live sync, `prices` table has **0** AMFI rows; all MF holdings `ltp/value=null`, `incomplete=true`. Portfolio `total_value` collapses to priced equities/ETFs only (~85k). `prices.failed` lists only Yahoo equity/SGB misses — MF NAV miss is silent. | MF NAVs refreshed via AMFI for holdings (and needed history); failures listed in `prices.failed`; valued MFs contribute to overview | Fresh DB → OAuth → import MF CSVs → `POST /sync` → check MF `ltp` / `SELECT count(*) FROM prices WHERE source='amfi'` |
| F2 | P0 | Kite holdings sync / instrument identity | Kite MF snapshot stores `symbol=ISIN` with `isin=NULL`, creating **separate** instruments from Console CSV rows that already have name + ISIN (e.g. named fund `INF966L01689` vs instrument symbol `INF966L01689`). Snapshot qty lands on ISIN-symbol rows; CSV tx on named rows → double instruments, broken reconcile, AMFI lookup by ISIN fails on kite rows. | Merge by ISIN (or map Kite MF tradingsymbol ISIN → existing instrument); one instrument per fund | Import MF CSV then `/sync`; inspect `instruments` for name row with ISIN + second row with `symbol=ISIN` and null isin |
| F3 | P1 | Yahoo symbol mapping / `POST /sync` | Failed: `ZOMATO`, `TATAMOTORS`, `TATAMTRDVR`, `SWANENERGY`, `HBLPOWER`, `TRIL`, `IDFC`, plus SGB symbols. Liquid renames/delists not resolved; SGB unsupported. | Best-effort Yahoo/BSE map + clear failed reasons; SGB may be P3 unsupported asset | `/sync` after equity CSV import; inspect `prices.failed` |
| F4 | P1 | `GET /portfolio/performance` contributors | Contributor list not sorted by weight (e.g. weight 0.05 before 0.94). Weights still sum ≈ 1 for valued rows. | Sorted by weight descending (spec/design) | Import + price a multi-holding book → `GET /portfolio/performance` |
| F5 | P2 | Holdings / metrics with incomplete prices | Overview ITD XIRR ≈ -90% and absolute loss ≈ -1.5M when most open MF qty unpriced but invested cost still counted from full tx history. | Either exclude unpriced open qty from portfolio totals with explicit incomplete breakdown, or block misleading headline metrics when material value missing | Same as F1 after sync |
| F6 | P2 | MF dust quantity | `UTI NIFTY 50 INDEX FUND` showed qty ≈ `5.68e-14` (float residue). | Treat near-zero qty as flat zero | Import MF history with full redeem; inspect holdings |
| F7 | P3 | `scripts/live_smoke.sh` | macOS `/bin/bash` 3.2: `EQUITY_CSVS[-1]` → `bad array subscript`; smoke stopped before sync. | **Fixed** in `268fb1c` (`LAST_EQ` index) | Run script under bash 3.2 |
| F8 | P3 | History coverage / reconcile | 32 reconcile diffs; EQ CSV ends 2026-01-22, MF 2026-03-05; weekend `trades_appended=0`. Amplifies F2 false splits. | Expected until fresh ≤365-day export + F2 fix | N/A — product/data gap |

## Notes
- Console max export window: 365 days; EQ and MF exported separately; users typically import by Indian FY
- GET `/auth/callback` worked for browser OAuth (`connected=true`)
- Multi-file import + FY labels + re-import `action` behaved as designed
- Do not trust overview/XIRR from this run until F1+F2 fixed and a second live pass completes
- Optional follow-up data: export EQ 2026-01-23→today and MF 2026-03-06→today after identity/price fixes
