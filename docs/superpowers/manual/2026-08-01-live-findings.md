# Live API findings — 2026-08-01

## Environment
- Date / time (IST):
- API commit SHA:
- Market open?: yes / no
- Equity CSV slices imported (basenames only):
- MF CSV slices imported (basenames only):
- Console total value (approx):
- Known CSV coverage end (EQ / MF):

## Checklist result
- [ ] Health
- [ ] Auth (login → callback → status)
- [ ] Equity + MF multi-file import (one request, FY slices)
- [ ] Wrong-input file rejected with re-import `action` (good files kept)
- [ ] Re-import idempotent (`new=0`)
- [ ] Sync + prices
- [ ] Overview / holdings / alerts / performance
- [ ] Gap/reconcile alerts explained by post-CSV history gap (or filed as bug)
- [ ] Settings override round-trip
- [ ] Logout → sync 401

## Bugs
| ID | Severity | Endpoint / area | Observed | Expected | Repro |
|----|----------|-----------------|----------|----------|-------|
| F1 | | | | | |

## Notes
- Console max export window: 365 days; EQ and MF exported separately; users typically import by Indian FY
-
