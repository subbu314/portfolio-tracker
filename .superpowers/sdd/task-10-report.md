# Task 10 Report: Eight scenario overlays

## Status

Complete.

## Implementation

- Added minimal fixture overlays for empty, stale, gap, import-error, unknown-category, missing-price, and negative-return scenarios.
- Retained existing logged-out auth overlay.
- Added handler scenario matrix covering all eight non-happy scenarios.

## TDD evidence

1. Added scenario matrix before overlays existed.
2. Verified RED: seven scenario cases failed because their overlays were absent; logged-out passed using existing overlay.
3. Added fixture overlays.
4. Verified GREEN: 10 handler tests passed.

## Verification

- `npm --prefix apps/web run test -- src/__tests__/handlers.test.ts`: 10 passed.
- `cd apps/web && npm test`: 146 API tests and 93 web tests passed.
- Overlay JSON validation and `git diff --check`: passed.
- Linter diagnostics: 0 errors.

## Self-review

- Overlay arrays replace the happy fixture only where item-level values must differ.
- Empty charts are unavailable with no points; pre-existing unavailable 3Y and 5Y fixtures remain shared.
- Nullable response fields are used for unavailable pricing metrics; required OpenAPI fields remain present through deep merge.

## Concerns

- Technical Standards MCP exposed no technical-standard tools during implementation.
# Task 10 Report — Reconcile + gap detection

## Status

Implemented holdings-vs-transaction reconciliation, calendar-day trade append gap
detection, alert aggregation, and `GET /portfolio/alerts`.

## Changes

- Added `transaction_implied_qty`, `reconcile_holdings`, `detect_gaps`, and
  `get_alerts` in `modules/reconcile.py`.
- Gap warnings provide exact Console Tradebook export dates, cover Equity and/or
  Mutual Funds, and direct users to CSV import or Sync now instead of manual
  transaction edits.
- Added `/portfolio/alerts` for Overview and Import consumers.
- Reused public `kite_auth.get_setting` / `kite_auth.set_setting` helpers and
  existing `last_sync_at` / `last_trade_append_at` keys.

## TDD evidence

- Reconcile mismatch test failed with an empty result before implementation.
- Gap test failed because `detect_gaps` was absent before implementation.
- Alert aggregation test failed because `get_alerts` was absent before implementation.
- Endpoint test failed with HTTP 404 before route implementation.
- Added coverage for buy/sell net quantity, matching holdings, missing timestamp,
  one-day boundary, same-day boundary, gap messaging, alert shape, and HTTP route.

## Validation

- `cd apps/api && uv run pytest tests/test_reconcile.py -v`: 9 passed.
- `npm run api:test`: 89 passed, 1 pre-existing TestClient deprecation warning.
- IDE diagnostics: no errors in changed Python files.
- `git diff --check`: passed.

## Self-review

- Scope matches Task 10 brief; no manual transaction mutation path added.
- Calendar-day threshold is explicit: no warning at zero or one day; warning after
  more than one day.
- Reconciliation excludes quantities equal within `1e-6`.
- Technical Standards MCP was unavailable during implementation; repository
  conventions and loaded engineering standards were applied.

## Concern

Root `npm test` cannot complete because `apps/web/package.json` does not exist yet.
API suite completes successfully before that expected future-task failure.

## Important findings follow-up

- Reconciliation now checks the union of holdings and transaction instrument IDs,
  treating either missing side as zero quantity.
- Added regression coverage for a transaction-only position with no holdings snapshot.
- Alerts with reconciliation mismatches now include Console CSV backfill, Kite
  re-sync, and no-manual-edit guidance independently of gap detection.
- Focused validation: `11 passed`; IDE diagnostics: no errors.

## Review Fix: Strengthen scenario-matrix assertions

**Status:** Complete. No fixture overlay changes required.

### Changes

Extended `it.each` scenario matrix in `handlers.test.ts` with stronger assertions while keeping existing checks:

- **empty:** `overview.total_value === 0`, `series-ITD available === false`
- **logged_out:** `last_sync_at === null` (in addition to `connected === false`)
- **gap:** `gap.message` and `suggested_to` truthy (alongside existing `suggested_from`)
- **import_errors:** `existing > 0` (alongside existing `flagged_rows`)
- **unknown_category:** holdings include `needs_category === true` (alongside benchmarks check)
- **missing_prices:** some holding has `value === null` (alongside existing `ltp === null`)
- **negative:** `gain_pct < 0` and `absolute_excess_pp < 0` (alongside existing `gain_inr < 0`)

All existing fixtures satisfied stronger assertions without modification.

### Validation

- `cd apps/web && npm test -- src/__tests__/handlers.test.ts`: 10 passed.
- `cd apps/web && npm test`: 93 passed (23 files).

### Commit

- `test(web): strengthen MSW scenario overlay assertions`

