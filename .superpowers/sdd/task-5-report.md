# Task 5 Report: `useCancellableQuery` + WindowKey series methods

## Status: DONE

## Implementation

- Added `useCancellableQuery`, cancelling prior requests on key changes, resetting query state, and skipping disabled queries.
- Typed series API windows with `WindowKey`.
- Moved Overview and holding-detail series loads to hook while preserving Overview page/action/chart error separation and holding core-load not-found mapping.

## TDD Evidence

- RED: `useCancellableQuery` suite failed because its module did not exist.
- GREEN: hook, Overview, HoldingDetail, and API suites passed (34 tests).

## Validation

- `cd apps/web && npm test` — PASS: 147 API tests and 160 web tests across 31 files.
- IDE diagnostics — clean.

## Self-review

- Confirmed commit scope contains only five Task 5 source/test files.
- Confirmed no whitespace errors with `git show --check`.

## Concerns

- Existing npm configuration warnings and one FastAPI TestClient deprecation warning remain unrelated to this task.

## Commit

- `66e34b0` refactor(web): add cancellable query hook for series loads

## Review Fix: key dependency identity

- Replaced variable-length effect dependencies with serialized `keyId`, ensuring key-content and key-length changes both restart the query, clear query state, and cancel superseded results.
- Added regression coverage for `["a"]` → `["a", "b"]`, asserting a second query begins and a superseded response cannot replace its result.

## Review Fix Validation

- `cd apps/web && npm test -- src/__tests__/useCancellableQuery.test.tsx src/__tests__/OverviewPage.test.tsx src/__tests__/HoldingDetailPage.test.tsx src/__tests__/api.test.ts` — PASS: 147 API tests; 35 web tests across 4 files.
- `cd apps/web && npm test` — PASS: 147 API tests; 161 web tests across 31 files.
- IDE diagnostics — clean.
