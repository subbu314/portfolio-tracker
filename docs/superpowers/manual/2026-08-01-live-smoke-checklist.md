# Live API smoke checklist — 2026-08-01

Run from repo root (worktree OK). Fill results in `2026-08-01-live-findings.md`.
On failure → append a bugs row; do not invent fixes mid-run unless blocking.

**Console facts:** tradebook export max **365 days**; Equity and MF are **separate** CSVs; users typically import by Indian FY (`FY2024-25` = 2024-04-01 → 2025-03-31).

**Locked CSV set** (under `$HOME/Downloads`, never commit):

| Basename | Segment | Approx FY |
|----------|---------|-----------|
| `tradebook-RYY010-EQ (2).csv` | EQ | FY2023-24 (partial) |
| `tradebook-RYY010-EQ (1).csv` | EQ | FY2024-25 |
| `tradebook-RYY010-EQ.csv` | EQ | FY2025-26 (partial) |
| `tradebook-RYY010-MF.csv` | MF | FY2023-24 |
| `tradebook-RYY010-MF (1).csv` | MF | FY2024-25 |
| `tradebook-RYY010-MF (2).csv` | MF | FY2025-26 (partial) |

Skip `MF (3)` (duplicate of MF (2)) except as an optional idempotency check.

**Expected history gaps (not necessarily bugs):** EQ CSV ends ~2026-01-22; MF ends ~2026-03-05. Gap/reconcile alerts after `/sync` are expected until a fresh ≤365-day export covers last CSV end → today.

---

## 1. Prerequisites

```bash
test -f .env && grep -q 'KITE_API_KEY=.\+' .env && echo "keys present" || echo "MISSING KEYS"
DL="$HOME/Downloads"
for f in \
  "tradebook-RYY010-EQ (2).csv" \
  "tradebook-RYY010-EQ (1).csv" \
  "tradebook-RYY010-EQ.csv" \
  "tradebook-RYY010-MF.csv" \
  "tradebook-RYY010-MF (1).csv" \
  "tradebook-RYY010-MF (2).csv"
do
  test -f "$DL/$f" && echo "ok $f" || echo "MISSING $f"
done
```

- [ ] `.env` ready; Kite redirect URL is exactly `http://127.0.0.1:8000/auth/callback`
- [ ] All six unique slice files present

---

## 2. Fresh DB + start API

```bash
mkdir -p data
rm -f data/portfolio.db
npm run api
```

In another terminal:

```bash
curl -sf http://127.0.0.1:8000/health
```

Expected: `{"status":"ok"}` and `data/portfolio.db` created.

- [ ] Health OK

---

## 3. OAuth (interactive)

```bash
curl -sf http://127.0.0.1:8000/auth/login-url
# Open login_url in browser; complete Zerodha login
# Browser lands on http://127.0.0.1:8000/auth/callback?request_token=…&action=login&status=success
# Page/body should show {"connected":true}
curl -sf http://127.0.0.1:8000/auth/status
```

Expected status:

```json
{
  "connected": true,
  "credentials_configured": true,
  "last_sync_at": null,
  "last_trade_append_at": null
}
```

If GET callback fails: copy `request_token` from the URL and:

```bash
curl -sf -X POST http://127.0.0.1:8000/auth/callback \
  -H 'Content-Type: application/json' \
  -d '{"request_token":"PASTE_TOKEN"}'
```

- [ ] Auth login → callback → status connected
- Log failures as `F-auth-*`

---

## 4. Multi-file import (EQ + MF FY slices)

Prefer:

```bash
./scripts/live_smoke.sh
```

Or manually:

```bash
BASE=http://127.0.0.1:8000
DL="$HOME/Downloads"
curl -sf -X POST "$BASE/import/csv" \
  -F "files=@${DL}/tradebook-RYY010-EQ (2).csv;type=text/csv" \
  -F "files=@${DL}/tradebook-RYY010-EQ (1).csv;type=text/csv" \
  -F "files=@${DL}/tradebook-RYY010-EQ.csv;type=text/csv" \
  -F "files=@${DL}/tradebook-RYY010-MF.csv;type=text/csv" \
  -F "files=@${DL}/tradebook-RYY010-MF (1).csv;type=text/csv" \
  -F "files=@${DL}/tradebook-RYY010-MF (2).csv;type=text/csv" \
  | tee /tmp/pt-import-batch.json
```

Expected: HTTP 200; `summary.rejected` = 0; `summary.accepted` = 6; each file has `financial_years`; `new` sums to total unique trades.

**Wrong-input check:**

```bash
curl -s -X POST "$BASE/import/csv" \
  -F "files=@${DL}/tradebook-RYY010-EQ.csv;type=text/csv" \
  -F "files=@/etc/hosts;type=text/csv" | tee /tmp/pt-import-partial.json
```

Expected: HTTP 200; `summary.accepted` ≥ 1; `summary.rejected` ≥ 1; rejected row `action` contains `import this file again`. Single bad `file=` alone → HTTP 400 with same `action`.

Idempotency: re-send batch or one `file=` → `new` = 0 for already-seen rows.

- [ ] Multi-file import accepted
- [ ] Wrong-input rejected with re-import `action`
- [ ] Re-import idempotent

---

## 5. Sync + prices

Already in `live_smoke.sh`; or:

```bash
curl -sf -X POST http://127.0.0.1:8000/sync
```

Expected:
- `holdings_count` ≈ Console holdings count
- `prices.updated` > 0 or failures listed in `prices.failed`
- `last_sync_at` set on subsequent `/auth/status`

- [ ] Sync + prices OK

---

## 6. Portfolio surfaces

Inspect `/tmp/pt-overview.json`, holdings, alerts, performance:

| Check | Pass if |
|-------|---------|
| `total_value` | Within ~5% of Console holdings value (LTP/NAV lag OK) |
| holdings qty | Match Console for 2 spot-checked symbols from Kite snapshot |
| `incomplete` | false when prices succeeded; true only with listed gaps |
| `windows.ITD` | non-null when history exists |
| `windows.1Y` / `3Y` / `5Y` | non-null only when inception allows |
| alerts.gap | **Expected** if CSV `date_max` ≪ today — record suggested range |
| alerts.reconcile | **Likely** until post-CSV trades imported; P1 only if diffs remain after fresh slice through today |
| performance.contributors | sorted; weights sum ≈ 1 for valued rows |
| rates | fractions (XIRR 0.18 not 18) |

- [ ] Overview / holdings / alerts / performance OK
- [ ] Gap/reconcile explained by history gap (or filed as bug)

---

## 7. Settings round-trip

```bash
# pick instrument_id from /settings/benchmarks
curl -sf -X PUT http://127.0.0.1:8000/settings/benchmarks/ID \
  -H 'Content-Type: application/json' \
  -d '{"benchmark_index":"Nifty Midcap 150"}'
curl -sf -X PUT http://127.0.0.1:8000/settings/categories/ID \
  -H 'Content-Type: application/json' \
  -d '{"category":"mid_cap"}'
curl -sf http://127.0.0.1:8000/settings/benchmarks
```

Expected: `source` = `user`; category updated.

- [ ] Settings override round-trip

---

## 8. Logout gate

```bash
curl -sf -X POST http://127.0.0.1:8000/auth/logout
curl -s -o /tmp/pt-sync-401.json -w "%{http_code}" -X POST http://127.0.0.1:8000/sync
```

Expected: HTTP `401`; body detail mentions reconnect.

- [ ] Logout → sync 401

---

## 9. Record findings

Update `2026-08-01-live-findings.md`. Strip tokens, account ids, full holdings lists.
