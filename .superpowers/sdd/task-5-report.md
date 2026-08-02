# Task 5 Report: Restyle shared controls, StatusBanner, and charts

## Status

DONE

## Implementation

- Migrated `WindowSelect` and metric controls from native selects to shadcn/Radix Select controls.
- Restyled `StatusBanner` with Alert and Button primitives while preserving `deriveStatusBanner` props and CTA behavior.
- Wrapped `ValueHero` and `MetricCard` in Card primitives; financial values use monospace tabular numerals and retain negative-value data attributes.
- Replaced chart loading copy with Skeleton, kept null series values as null, added muted empty/unavailable panels, and tokenized allocation colors.
- Added Radix/jsdom pointer-capture and scrolling test shims.

## TDD Evidence

- RED: Radix click-pattern tests failed against native selects because option clicks did not invoke callbacks.
- GREEN: focused shared-control and overview tests passed after Select migration and required jsdom shims.

## Validation

- `cd apps/web && npm test` — PASS: API 146 passed, OpenAPI check passed, web 74 passed across 20 files.
- `cd apps/web && npm run lint` — PASS.
- `git diff --check` — PASS.
- IDE diagnostics for modified files — clean.

## Self-review

- All former `user.selectOptions` calls now exercise combobox/option interaction.
- Accessible labels preserve contextual window and metric names, including `Portfolio chart window`.
- Chart mapping retains `null` data points; no unavailable metric is converted to zero.
- No metric formulas or API contracts changed.

## Concerns

- Existing npm configuration warnings and Starlette/httpx deprecation warning remain in test output.

## Commit

- `feat(web): restyle shared controls, banners, and charts`

## Review Fixes

- Rendered unavailable MetricCard values as muted `N/A` text without the primary `metric-value` class.
- Rendered a null ValueHero gain percentage as muted `N/A` text without the positive `metric-percent` class.
- Added monospace tabular numerals to ValueHero invested-cost INR value.
- Added focused assertions that unavailable values use `text-muted-foreground` and do not retain their primary styling classes.

## Review Fix Validation

- `npm --prefix apps/web run test -- OverviewCards.test.tsx` — PASS: 1 file, 7 tests passed.
