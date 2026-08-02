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
