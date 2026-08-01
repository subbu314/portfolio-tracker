# Task 9 Report: Kite sync

## Status

Implemented Kite Personal holdings sync, same-day trade append, auth invalidation,
price refresh orchestration, and `POST /sync`.

## Changes

- Added equity, ETF, and mutual-fund holdings snapshot upserts.
- Added IST same-day trade filtering with stable API dedupe keys.
- Added idempotent re-sync behavior and sync timestamp settings.
- Added Kite auth-error invalidation, committed token removal, and secret-safe errors.
- Added sync router with reconnect response and Yahoo/AMFI price refresh.
- Registered sync router in application.

## TDD evidence

- Core sync test first failed because `kite_sync` did not exist, then passed after implementation.
- Auth invalidation test failed with unhandled `TokenException`, then passed after guarded Kite calls.
- Endpoint test failed with HTTP 404, then passed after router implementation and registration.

## Validation

- `cd apps/api && uv run pytest -q`: 79 passed.
- IDE diagnostics: no errors in changed files.
- `git diff --check`: passed.
- Existing Starlette `TestClient` deprecation warning remains.

## Self-review

- Confirmed no Kite market-data calls; pricing remains Yahoo/AMFI.
- Confirmed API errors never return upstream token-bearing text.
- Confirmed duplicate trades skip and holdings update in place.
- Confirmed non-auth Kite failures propagate without clearing valid credentials.

## Stale snapshot cleanup (2026-08-01)

### Finding

Sync only upserted Kite holdings; sold/exited positions kept stale `HoldingsSnapshot`
rows and stayed visible in portfolio assembly.

### Fix

- Track synced instrument IDs during equity/MF upserts.
- After upserts, `_remove_stale_holdings` deletes snapshots whose `instrument_id`
  is not in the returned Kite set (handles prior `as_of` dates; empty Kite response
  clears all snapshots).
- `invalidate_on_kite_error` unchanged in `_fetch_kite_data`.

### Regression test

- `test_sync_removes_stale_snapshot_for_sold_symbol`: pre-seeded SOLD snapshot
  removed after sync returning only RELIANCE.

### Validation

- `uv run pytest tests/test_kite_sync.py -v`: 6 passed.
- `uv run pytest -q`: full suite run after fix.

## Concerns

- Technical Standards MCP was unavailable during implementation, so no additional
  company-standard corpus could be loaded.
