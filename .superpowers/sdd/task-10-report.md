# Task 10 Report: P3 leftovers and mock polish

## Status

DONE

## Implementation

- FE-LIB-7: Normalized one trailing slash from `NEXT_PUBLIC_API_URL`.
- FE-LIB-6: Treated unparseable sync timestamps as null/stale.
- FE-LIB-10: Bucketed unknown instrument types under `Other`.
- FE-UI-11: Reloaded auth, benchmark settings, and catalogs after sync.
- FE-LIB-8: Rejected batch-shaped and otherwise invalid stored import reports.
- FE-MOCK-6/7/8: Made missing-price totals, allocation, and ITD series unavailable; warned on missing overlays; nulled logged-out trade append time.
- FE-CFG-3/4 and FE-TEST-4: Failed closed on MSW startup errors and warned on unhandled requests.

## TDD Evidence

- FE-LIB-7 RED: request URL contained `//health`. GREEN: focused API regression passed.
- FE-LIB-6 RED: invalid timestamp produced no banner. GREEN: status suite passed 7 tests.
- FE-LIB-10 RED: unknown type inflated Equity to 100%. GREEN: allocation suite passed 4 tests.
- FE-UI-11 RED: benchmark settings loaded once after sync. GREEN: Settings suite passed 4 tests.
- FE-LIB-8 RED: batch-shaped JSON was returned as an import report. GREEN: ImportReport suite passed 12 tests.
- FE-MOCK-6/7/8 RED: stale totals/series/trade timestamp leaked from happy fixtures and no warning was emitted. GREEN: focused handlers regressions passed 4 tests.
- FE-CFG-3/4 RED: startup failure rendered children and worker bypassed unhandled requests. GREEN: MockProvider suite passed 5 tests.

## Validation

- `cd apps/web && npm test` — PASS: 27 files, 146 tests.
- IDE diagnostics for changed source files: clean.

## Commits

- `6a0d025 fix(web): normalize trailing slash in API base URL`
- `2b77c15 fix(web): treat invalid sync dates as stale`
- `ef50fe4 fix(web): bucket unknown instrument types as other`
- `90788c3 fix(web): reload settings after holdings sync`
- `2932d45 fix(web): validate stored import report shape`
- `0cdb26a fix(web): make missing-price mocks honest`
- `fe46878 fix(web): fail closed when mock worker startup fails`

## Concerns

- npm emits pre-existing unsupported-config warnings for `devdir`, `always-auth`, and `email`.
- `npm ci` reports three high-severity dependency vulnerabilities; remediation is outside this task.
- Unrelated pre-existing working-tree changes remain uncommitted.

## Important Review Findings

- FE-LIB-8: Strengthened stored import-report validation for every required report field; discriminator-only JSON now returns null.
- FE-MOCK-6: Added unavailable missing-price portfolio-series overlays for 1Y, 3Y, and 5Y, preventing happy-series fallback.

## Important Review Validation

- `npm --prefix apps/web test -- src/__tests__/ImportReport.test.tsx src/__tests__/handlers.test.ts` — PASS: 2 files, 26 tests.
- `cd apps/web && npm test` — PASS: 27 files, 147 tests.
- IDE diagnostics for changed TypeScript files: clean.
- Fix commit: `0aa6a37 fix(web): close important Task 10 findings`.

