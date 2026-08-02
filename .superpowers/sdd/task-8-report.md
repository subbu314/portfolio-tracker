# Task 8 Report

## Status

Complete.

## Implementation

- Added Settings account panel for logged-out and logged-in states.
- Wired Zerodha login URL retrieval and holdings synchronization.
- Added credentials configuration warning and `.env` guidance without exposing secrets.
- Added data-driven benchmark and mutual-fund category selectors.
- Added browser OAuth callback exchange and redirect to `/settings`.
- Updated `.env.example` to use the Next.js callback URL while preserving the API smoke alternative.
- Left `api-types.ts`, `openapi.json`, and `api.ts` unchanged.

## TDD Evidence

- RED: `SettingsAuth.test.tsx` failed because `SettingsAuthPanel` did not exist.
- GREEN: focused suite passed with 2 tests.

## Validation

- `npm test`: 146 API tests and 62 web tests passed; OpenAPI client freshness check passed.
- `npm run build` in `apps/web`: production build and type validation passed.
- IDE lint diagnostics: no errors in changed TypeScript files.

## Commit

`ecc64c5 feat(web): add Settings auth, sync, and benchmark overrides`

## Concerns

- Live Zerodha OAuth was not exercised because it requires configured credentials and an interactive external login.
- Existing npm configuration deprecation warnings and one Starlette dependency warning remain.
- Pre-existing unrelated report and plan working-tree changes were not included in the commit.
# Task 8 Report: Regeneration workflow docs + end-to-end smoke

## Status: DONE_WITH_CONCERNS

## Commit

- `67eebe1` docs: document OpenAPI TypeScript regeneration workflow

## Implementation

- Created root `README.md` with project title, one-line blurb, and Frontend ↔ API contract.
- Documented schema source of truth, `npm run generate:api`, committed generated artifact paths, direct browser API URL, and allowed CORS origin.
- Regeneration completed without changing `apps/web/openapi.json` or `apps/web/src/lib/api-types.ts`.

## Full Smoke

```text
$ cd apps/api && uv run pytest -q
124 passed, 1 warning in 3.36s

$ npm run generate:api
Wrote ../web/openapi.json
✨ openapi-typescript 7.13.0
🚀 ./openapi.json → ./src/lib/api-types.ts [41.9ms]

$ cd apps/web && npm test && npx tsc --noEmit
Test Files  2 passed (2)
Tests  7 passed (7)
TypeScript compiler exited 0.
```

## Concerns

- Pytest emits existing Starlette `httpx` deprecation warning.
- Vitest emits existing ESM/CommonJS config-loader warning.
- npm emits existing unsupported config warnings for `devdir`, `always-auth`, and `email`.
- Unrelated pre-existing working-tree changes were left untouched.

## Important review fix: once-only OAuth exchange

- Guarded callback exchange by request token so React Strict Mode effect replay cannot reuse a single-use Kite token.
- Added `AuthCallback.test.tsx`, rendering callback under `StrictMode`.
- RED: `npm test -- src/__tests__/AuthCallback.test.tsx` — callback test failed: expected 1 call, received 2.
- GREEN: `npm --prefix apps/web test -- src/__tests__/AuthCallback.test.tsx src/__tests__/SettingsAuth.test.tsx` — 2 files passed, 3 tests passed.
- FULL: `cd apps/web && npm test` — 15 files passed, 63 tests passed.
