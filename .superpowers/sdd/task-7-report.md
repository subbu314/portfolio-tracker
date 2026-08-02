# Task 7 Report: Metrics

**Status:** Done. All interfaces from brief implemented in `apps/api/src/portfolio_tracker/modules/metrics.py`, TDD'd in `apps/api/tests/test_metrics.py`.

## Commits

- `9dd49b7` — feat: add metrics module (absolute, CAGR, XIRR, excess, rolling windows)

## Tests

22 tests in `test_metrics.py` (10 from brief verbatim + 12 added for `rolling_absolute`, `rolling_cagr`, `window_metric_bundle`, `benchmark_xirr_from_trades` with opening MV, and edge cases). Full API suite: 63 passed.

## Deviations from brief's reference code (both required to pass the brief's own tests)

1. **`numpy_financial` has no `xirr`** (only evenly-spaced `irr`/`npv`). Implemented a bisection XNPV solver instead (expands bracket, then bisects to `<1e-9` residual). No new dependency.
2. **Day-count: actual/365, not 365.25.** Brief's reference `cagr()` used `days/365.25`, which misses the brief's own test tolerance (`test_cagr_requires_365_days` expects `abs(value - 0.1) < 1e-6`; 365.25 gives `0.100047`, off by 4.7e-5). Switched to `days/365.0` for both `cagr` and `xirr`, consistent with `WINDOW_DAYS` already being plain 365/1095/1825.

## Self-review vs locked excess rules

- `absolute_excess_pp`: `window_metric_bundle` diffs cost-based absolute `gain_pct` vs `bench_return` (point-to-point) — matches.
- `cagr_excess_pp`: diffs `cagr_value` vs `bench_cagr` — matches.
- `xirr_excess_pp`: diffs `xirr_value` vs `bench_xirr`; callers must supply `bench_xirr` from `benchmark_xirr_from_trades` (same ₹ cashflows into mapped index), never a raw point-to-point bench return. Verified via `test_benchmark_xirr_same_cashflows_not_point_to_point`.
- No conflicts found between brief and locked rules — brief's own "Excess:" bullet already states the same rule.

## Concerns

- `window_metric_bundle` and `rolling_absolute`/`rolling_cagr` are my additions (brief listed them as required interfaces but gave no sample code/tests) — worth a second look when wired into callers (portfolio/holdings endpoints) to confirm the exact field names match downstream expectations.
- No metrics_cache, no I/O — confirmed pure per brief.

**Report path:** `.superpowers/sdd/task-7-report.md`

## XIRR Solver Follow-up

**Status:** Critical/Important findings fixed with regression-first TDD.

- Same-day cashflows now return `None` when every day offset is zero, preventing a spurious bisection rate for zero-sum buy/terminal flows.
- Solver now fails soft with `None` for `ZeroDivisionError`, `OverflowError`, and `ValueError`.
- Added regressions for same-day zero-sum flows and an extreme date range that previously raised `ZeroDivisionError`.
- Metrics tests: 24 passed. Full API suite: 65 passed, 1 third-party deprecation warning.
- Locked excess formulas and window logic unchanged.
