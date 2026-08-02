# Final whole-branch review fix report

## Fixes

- Completed Tailwind v4 `@theme inline` mappings for shadcn semantic colors while preserving polish palette.
- Made `missing_prices` overview, holdings list, and holding details consistently expose unavailable price-dependent values and metrics as `null`; marked affected data incomplete.
- Registered new holding detail overlays in static fixture registry.
- Excluded holdings with unavailable values from allocation calculations.
- Added regression coverage for theme mappings, allocation null handling, and missing-price scenario responses.

## Validation

### Web tests

Command:

```text
npm --prefix apps/web test
```

Result:

```text
Test Files  26 passed (26)
Tests       107 passed (107)
Exit code   0
```

### Production build

Command:

```text
npm --prefix apps/web run build
```

Result:

```text
Next.js 15.5.22
Compiled successfully
Linting and checking validity of types completed
Generated static pages (10/10)
Exit code 0
```

## Notes

- npm emitted existing deprecation warnings for user configuration keys (`devdir`, `always-auth`, `email`); tests and build succeeded.
