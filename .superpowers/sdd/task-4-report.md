# Task 4 Report: Portfolio absolute return series

## Status

DONE

## TDD

### RED

Added `apps/api/tests/test_portfolio_series.py` and the portfolio-series OpenAPI
assertion before production code.

Command:

`cd apps/api && uv run pytest tests/test_portfolio_series.py tests/test_openapi_portfolio.py::test_openapi_includes_portfolio_series -v`

Result: 4 expected failures. Service export was absent, HTTP route returned 404,
invalid-window request returned 404, and OpenAPI path/schema entries were absent.

### GREEN

Implemented schemas, service, module export, and collection route.

Targeted command:

`cd apps/api && uv run pytest tests/test_portfolio_series.py tests/test_openapi_portfolio.py -v`

Result: 7 passed, 1 pre-existing Starlette deprecation warning.

## Implementation

- Added portfolio absolute cumulative return points and weighted benchmark return
  points for `ITD`, `1Y`, `3Y`, and `5Y`.
- Added unavailable-window and incomplete-data response handling.
- Added `GET /portfolio/series?window=ITD` before instrument-specific routes.
- Added `SeriesPoint` and `PortfolioSeriesResponse`.
- Preserved HTTP 400 for unsupported windows while publishing allowed values in
  query-parameter OpenAPI.
- Regenerated `apps/web/openapi.json` and `apps/web/src/lib/api-types.ts`.
- Did not modify handwritten `apps/web/src/lib/api.ts`.
- Did not implement holding-series behavior.

## Files changed

- `.superpowers/sdd/task-4-report.md`
- `apps/api/src/portfolio_tracker/modules/portfolio/series.py`
- `apps/api/src/portfolio_tracker/modules/portfolio/__init__.py`
- `apps/api/src/portfolio_tracker/schemas/portfolio.py`
- `apps/api/src/portfolio_tracker/routers/portfolio.py`
- `apps/api/tests/test_portfolio_series.py`
- `apps/api/tests/test_openapi_portfolio.py`
- `apps/web/openapi.json`
- `apps/web/src/lib/api-types.ts`

## Validation

- `npm run generate:api`: passed.
- `cd apps/api && uv run pytest -q`: 138 passed, 1 warning.
- `npm run check:api`: passed.
- IDE diagnostics: one Sonar cognitive-complexity warning on
  `get_portfolio_series`; implementation intentionally follows supplied brief.

## Self-review

- Route is a `/portfolio` collection route and precedes parameterized routes.
- Response model forbids extra fields and exposes nullable holding return for
  Task 5 compatibility.
- Generated TypeScript query parameter retains the four-value window union.
- Task-scoped files only will be committed; unrelated working-tree changes remain
  untouched.

## Concerns

- Existing FastAPI TestClient emits a Starlette/httpx deprecation warning.
- Sonar reports cognitive complexity 30 for brief-supplied series algorithm.
