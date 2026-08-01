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
