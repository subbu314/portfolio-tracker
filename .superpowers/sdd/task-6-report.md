# Task 6 Report: Honest empty + negative mock overlays

## Status: DONE

## Implementation

- Empty overview now nulls every return and window metric and supplies empty allocation.
- Negative overview now overrides top-level and available-window returns with negative values while preserving consistent negative excess signs.
- Handler and rendered scenario tests enforce honest merged fixtures and unavailable-value UI.

## TDD Evidence

- RED: focused suite failed 2 tests because empty and negative overlays inherited happy `xirr: 0.15`.
- GREEN: focused suite passed 15 tests across 2 files.

## Validation

- `npm --prefix apps/web test` — PASS: 116 tests across 26 files.
- IDE diagnostics for modified test files — clean.

## Concerns

- Existing npm configuration warnings remain in test output.
- Pre-existing unrelated worktree changes were left untouched.

## Commit

- `5773559 fix(web): make empty and negative overview mocks honest`

## Important Review Follow-up

- Overview scenario assertions now scope checks to real `Portfolio return` and `Outperformance` cards.
- Empty scenario requires both card values to be `N/A`, excludes inherited `15.00%`, and excludes positive benchmark copy.
- Negative scenario requires `-12.00%`, `-2.50 pp`, and trailing-benchmark copy while excluding inherited happy values.
- Handler coverage now checks `gain_pct`, `cagr`, `absolute_pct`, and `1Y` window overlays.

### Commands + Output

- `cd apps/web && npm test -- src/__tests__/Overview.scenarios.test.tsx src/__tests__/handlers.test.ts`
  - PASS: 2 files, 16 tests; API 146 passed; API schema check passed.
- `cd apps/web && npm test`
  - PASS: 26 files, 117 web tests; API 146 passed; API schema check passed.
