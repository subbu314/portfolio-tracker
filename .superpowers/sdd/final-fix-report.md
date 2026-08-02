# Final Fix Report: UI API Gaps

## Status

Complete. Left locked `MV(t) / MV(base) - 1` formula unchanged.

## What Changed

- Portfolio series now skips incomplete base days until every held instrument has a usable forward-filled price. Days with missing held-instrument prices produce `portfolio_return: null` and set `incomplete: true`; no partial market value is used.
- Added regression coverage for two holdings where one price history starts late. Base moves to first fully priced day, so no fabricated `+100%` return occurs.
- Batch-loaded portfolio prices, benchmark maps, and benchmark levels, then forward-filled each series in memory. Portfolio series now uses bounded bulk queries instead of price and benchmark lookups for every holding/day. Daily source-price points remain unchanged.
- Removed unused `MF_CATEGORY_CHOICES`.

## Tests

- `cd apps/api && uv run pytest -q tests/test_portfolio_series.py` — 10 passed, 1 existing Starlette deprecation warning.
- `cd apps/api && uv run pytest -q` — 146 passed, 1 existing Starlette deprecation warning.
- IDE diagnostics: no errors in changed portfolio series or tests. Existing Sonar warning in `benchmarks.py` reports repeated `"Nifty 500"` literals; unchanged except for removal of unused constant.

## Commits

- `2bdf9c0 fix(api): prevent partial-price portfolio return spikes`

## Remaining Concerns

- Series output dates remain source price dates plus window boundaries, as before; no synthetic calendar dates were added.
- Query reduction is structural rather than benchmarked: portfolio prices and benchmark levels are each read once per series, then forward-filled in memory.
# Final whole-branch review fixes

## Result

- Restored `TOKEN_UPDATED_KEY` to `kite_token_updated_at`.
- Confirmed token exchange and clearing use `TOKEN_UPDATED_KEY`; added regression coverage for its persisted name.
- Flattened active frontend plan's `Performance` type and Task 15 window accessors.
- Preserved Lean UI constraints block unchanged.
- Narrowed public `get_overview` by removing its computed-holdings keyword argument; `get_performance` continues through `_get_overview_from_computed`.

## Verification

- Targeted API tests: 32 passed, 1 dependency deprecation warning.
- Full API suite: 118 passed, 1 dependency deprecation warning.
- Edited Python files: no linter errors.

## Commit

`fix: restore kite token key; align Performance docs with flat payload`

## OpenAPI review-fix follow-up

### Changes

- Root `check:api` now runs only the web API type-drift check; live-app-to-OpenAPI validation remains in pytest.
- Web API drift check creates and removes `apps/web/.api-types.check.ts`, outside `src/`.
- Removed unused `WindowMetrics` import from portfolio schemas.

### Verification

- `cd apps/api && uv run pytest tests/test_openapi_export.py tests/test_schemas_common.py tests/test_openapi_portfolio.py -q`: 7 passed, 1 Starlette deprecation warning.
- `cd apps/web && npm run check:api`: passed; generated and removed `.api-types.check.ts`.
- `cd apps/web && npm test`: passed; root test script ran 127 API tests and 20 web tests. Warnings: Starlette deprecation and Vitest ESM configuration notice.
- `npm run check:api && git diff --exit-code -- apps/web/openapi.json`: passed; `apps/web/openapi.json` remained unchanged.
