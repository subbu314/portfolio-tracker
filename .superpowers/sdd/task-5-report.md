# Task 5 Report: Kill `_benchmark_cagr` leak

## Status

DONE

## Implementation

- Added `HoldingPublic` and `HoldingComputed` typed dictionaries in
  `apps/api/src/portfolio_tracker/modules/portfolio_types.py`.
- Added internal computed holding assembly with public fields isolated under
  `HoldingComputed.public`.
- Changed `get_holdings` to return only `HoldingPublic` rows.
- Changed overview benchmark blending to consume
  `HoldingComputed.benchmark_cagr`.
- Removed `_benchmark_cagr` cleanup from portfolio router and
  `get_performance`; private key is no longer created on public rows.
- Preserved one holding computation in `get_performance`.

## TDD Evidence

1. Added `test_holdings_rows_never_contain_private_benchmark_cagr_key`.
2. RED: focused test failed because module-level holding contained
   `_benchmark_cagr`.
3. GREEN: focused leak, single-call, and HTTP tests passed: 3 passed.

## Verification

- Required targeted command:
  `uv run pytest tests/test_portfolio.py tests/test_api_integration.py -q`
  — 18 passed.
- Full API suite:
  `uv run pytest -q`
  — 111 passed.
- IDE lint diagnostics: no errors.
- `git show --check`: no whitespace errors.

One pre-existing Starlette/httpx deprecation warning remains in test output.

## Self-review

- Public holding rows contain neither `_benchmark_cagr` nor
  `benchmark_cagr`.
- `windows` remains part of each public holding row.
- Benchmark CAGR remains available only through typed internal computed rows.
- Router and performance code no longer perform boundary cleanup.
- No Task 7 package split or unrelated refactor was introduced.
- Existing untracked plan documents were left untouched.

## Commit

`58d27e9 refactor: stop leaking private benchmark_cagr on holding rows`

## Concerns

None task-related.

## Critical Review Fix

- Removed public-field reconstruction of `benchmark_cagr`.
- Added one internal `HoldingComputed` path shared by overview and performance
  assembly; public `get_holdings` still returns only `HoldingPublic`.
- Updated the single-computation regression to cover
  `_get_holdings_computed`.
- Covering tests:
  `test_holdings_rows_never_contain_private_benchmark_cagr_key` and
  `test_overview_itd_cagr_excess_uses_internal_benchmark_cagr` in
  `apps/api/tests/test_portfolio.py`.
- RED: numerical regression failed with `364.0854444662689` instead of
  `3.640854444662689`.
- Focused regressions: 3 passed, 1 pre-existing warning.
- Required command:
  `cd apps/api && uv run pytest tests/test_portfolio.py tests/test_api_integration.py -q`
  — 19 passed, 1 pre-existing warning.
- Full suite:
  `cd apps/api && uv run pytest -q`
  — 112 passed, 1 pre-existing warning.
- IDE lint diagnostics: no errors.
