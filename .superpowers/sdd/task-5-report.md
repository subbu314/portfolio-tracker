# Task 5 Report: Price providers and cache

## Status

Implemented Yahoo Finance and AMFI price providers plus database-backed price
refresh for instruments and benchmarks.

## Delivered

- Added `PriceProvider` protocol and injectable Yahoo/AMFI provider implementations.
- Locked benchmark names to required Yahoo tickers.
- Added equity symbol resolution with `.NS` then `.BO` fallback on empty history
  or missing LTP, persisting successful symbol.
- Added AMFI ISIN resolution, NAV date/value mapping, scheme-code persistence,
  and mutual-fund category normalization.
- Added `Price` and `BenchmarkPrice` upsert caching.
- Added incremental refresh starting from latest cached date.
- Kept all unit tests offline with injected mocks and AMFI fixture data.

## TDD evidence

1. Added provider/cache tests before production modules.
2. Confirmed RED with `ModuleNotFoundError` for
   `portfolio_tracker.modules.prices`.
3. Added minimal production implementation.
4. Confirmed focused suite: `8 passed`.

## Verification

- `cd apps/api && uv run pytest -v`: 35 passed.
- IDE lint diagnostics: no errors in changed Python files.
- Existing Starlette deprecation warning remains in full suite.

## Self-review

- Confirmed required ticker mapping exactly matches task brief.
- Confirmed no Kite market-data integration was added.
- Confirmed existing user-selected MF category is not overwritten.
- Confirmed empty `benchmark_names` disables benchmark refresh for callers/tests.
- No known functional concerns within Task 5 scope.

## Important findings follow-up

- Same-day incremental refresh now fetches and upserts LTP when Yahoo history is
  empty, without marking the refresh incomplete.
- A stored `.NS` Yahoo symbol now retains `.BO` fallback when `.NS` misses.
- A stored AMFI `scheme_code` is used directly for NAV history and category
  lookup, avoiding an ISIN search; newly discovered codes remain persisted.
- Index ticker mappings and the `PriceProvider` protocol are unchanged.

### Covering tests

- `test_refresh_prices_updates_ltp_when_same_day_history_is_empty`
- `test_refresh_prices_tries_bse_after_stored_nse_symbol_fails`
- `test_refresh_prices_reuses_stored_amfi_scheme_code`

### Commands and output

- RED: `uv run pytest -v tests/test_prices.py -k 'same_day_history or stored_nse_symbol or stored_amfi_scheme_code'`
  → `3 failed`.
- Focused GREEN: `uv run pytest -v tests/test_prices.py`
  → `11 passed`.
- Full API regression: `uv run pytest -v`
  → `38 passed, 1 warning in 1.43s`.
- IDE lint diagnostics: no errors in changed Python files.
- Warning is the pre-existing Starlette `httpx` deprecation from
  `fastapi.testclient`.
