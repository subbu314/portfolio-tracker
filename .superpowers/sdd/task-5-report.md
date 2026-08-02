# Task 5 Report: Holding absolute return series

## Status

DONE

## Implementation

- Added `get_holding_series(session, instrument_id, as_of, window)`.
- Added holding and mapped-index absolute return points using last close on or before each candidate day.
- Candidate dates use sorted unique price dates plus both `start` and `as_of`, matching portfolio-series forward-fill behavior.
- Added unavailable, incomplete, unknown-instrument, and invalid-window handling.
- Added `HoldingSeriesResponse` and `GET /portfolio/holdings/{instrument_id}/series`.
- Exported service through `portfolio_tracker.modules.portfolio`.
- Regenerated `apps/web/openapi.json` and `apps/web/src/lib/api-types.ts`; handwritten `api.ts` unchanged.

## TDD Evidence

- RED: four scoped tests failed because service, route, and OpenAPI schema were absent.
- GREEN: holding calculation, HTTP route, and OpenAPI tests passed after implementation.
- Candidate-date mutation check: replacing sorted `{start, as_of}` candidates with older as-of-only behavior caused both forward-fill cases to fail with first point `2024-06-01` instead of `2023-06-02`; restored implementation passed.

## Validation

- `npm run generate:api` — PASS.
- `npm run check:api` — PASS.
- `cd apps/api && uv run pytest -q` — PASS: 145 passed, 1 warning.
- `git diff --check` — PASS.
- IDE diagnostics found only pre-existing cognitive-complexity warning on `get_portfolio_series`.

## Self-review

- Formula matches requirement: `price(day) / price(base_day) - 1`; benchmark uses same base-day rule.
- Unknown instrument returns `None` in service and HTTP 404 in router.
- Response model forbids undeclared top-level fields and reuses `SeriesPoint`.
- No unrelated source changes included.

## Concerns

- Existing Starlette/httpx deprecation warning remains in test output.
- Existing Sonar cognitive-complexity warning remains on portfolio-series function outside Task 5 scope.

## Commit

- `feat(api): add holding absolute return series for detail charts`
