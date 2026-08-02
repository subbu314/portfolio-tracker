# Task 4 Report: Overview page

## Status

DONE

## Implementation

- Added portfolio value hero using `overview.total_value` and `overview.absolute`.
- Added independent return and outperformance cards with local Metric and Window controls.
- Added Absolute-only portfolio/category benchmark series chart with explicit unsupported and unavailable states.
- Added holdings-derived allocation donut using `allocationByKind`.
- Added client orchestration for overview, holdings, auth, alerts, series, and refresh APIs.
- Replaced placeholder home page and added responsive overview styling.

## TDD Evidence

- RED: `OverviewCards.test.tsx` failed because `MetricCard` and `ValueHero` did not exist.
- GREEN: focused suite passed all 4 tests after minimal component implementation.
- Full web suite passed all 48 tests across 9 files.

## Validation

- `cd apps/web && npm test` — PASS: 48 passed.
- `cd apps/web && npm run lint` — PASS.
- `cd apps/web && npm run build` — PASS.
- `git diff --check` — PASS.
- IDE diagnostics — no errors.

## Self-review

- ValueHero remains independent of Window controls.
- Cards read only `overview.windows[window]`; default Metric is XIRR.
- Series API runs only for Absolute metric; XIRR/CAGR clear series and show required copy.
- Allocation reads holdings by instrument type, not `overview.allocation`.
- No `getPerformance` call or API schema changes introduced.
- Null metrics format as `N/A`, never numeric zero.
- Existing unrelated working-tree changes remain untouched.

## Concerns

- Technical Standards MCP was unavailable during implementation; repository patterns and supplied standards were applied.
- Existing npm configuration and Starlette/httpx deprecation warnings remain outside Task 4 scope.

## Commit

- `feat(web): ship Overview with returns, chart, and allocation`
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

## Fix round: portfolio series base date

- Included `start` and `as_of` in sorted, unique candidate dates so forward-filled
  prices can establish market value on window start.
- Added regression coverage for a holding owned before window start whose latest
  price is before start, both with and without an `as_of` quote.
- OpenAPI schema is unchanged; API client regeneration was not needed.

### TDD RED

Command:

`cd apps/api && uv run pytest tests/test_portfolio_series.py::test_portfolio_series_uses_window_start_with_forward_filled_price -q`

Result: 2 failed as expected; both cases returned `2023-12-01` instead of
window start `2023-06-02`.

### Covering test

Command:

`cd apps/api && uv run pytest tests/test_portfolio_series.py -q`

Result: 5 passed, 1 pre-existing Starlette deprecation warning.

### Full suite

Command:

`cd apps/api && uv run pytest -q`

Result: 140 passed, 1 pre-existing Starlette deprecation warning in 3.91s.

## Fix round: Overview chart review findings

- Added explicit `N/A` to unsupported XIRR/CAGR series-chart copy.
- Clear prior chart series before each metric/window request and ignore superseded
  request success or failure callbacks.
- Covering tests:
  `apps/web/src/__tests__/OverviewCards.test.tsx` and
  `apps/web/src/__tests__/OverviewPage.test.tsx`.

### TDD RED

- `npm test -- src/__tests__/OverviewCards.test.tsx` — failed as expected:
  unsupported-metric copy omitted `N/A`.
- `VITE_CONFIG_NATIVE_IGNORE_WARNING=true node node_modules/vitest/vitest.mjs run src/__tests__/OverviewPage.test.tsx`
  — 2 failed as expected: old series remained during window loading and a late
  superseded response replaced current-window data.

### Covering tests

- `VITE_CONFIG_NATIVE_IGNORE_WARNING=true node node_modules/vitest/vitest.mjs run src/__tests__/OverviewCards.test.tsx src/__tests__/OverviewPage.test.tsx`
  — PASS: 2 files, 7 tests.

### Full suite

- `cd apps/web && npm test` — PASS: API 146 tests, generated API check,
  web 10 files / 51 tests. One pre-existing Starlette deprecation warning.
