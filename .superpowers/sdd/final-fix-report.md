# Final Important findings fix report

## Fixes

- Replaced `ScenarioSwitcher` static fixture-loader import with an on-demand import used only for `import_errors`.
- Cleared stale session import reports when selecting any other mock scenario.
- Corrected `missing_prices` absolute return to contract-valid values: current value `0`, invested cost `77500`, gain INR `-77500`, and gain percentage `-1`.
- Added regression coverage for deferred fixture loading, seed cleanup, and missing-price return consistency.

## TDD evidence

### RED

Command:

```text
cd apps/web && npm test -- src/__tests__/ScenarioSwitcher.test.tsx src/__tests__/handlers.test.ts
```

Result:

```text
Test Files  2 failed (2)
Tests       2 failed | 15 passed (17)
Failures    stale import seed remained; missing-price gain values were null
Exit code   1
```

Additional deferred-import assertion:

```text
Test Files  1 failed (1)
Tests       2 failed | 2 passed (4)
Failure     fixture module loaded during ScenarioSwitcher import
Exit code   1
```

### GREEN

```text
Test Files  2 passed (2)
Tests       17 passed (17)
Exit code   0
```

## Validation

### Web tests

Command:

```text
cd apps/web && npm test
```

Result:

```text
Test Files  27 passed (27)
Tests       148 passed (148)
Exit code   0
```

### Production build

Command:

```text
cd apps/web && npm run build
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
- IDE diagnostics reported no errors in changed TypeScript files.
- Commit: `fix(web): address final important review findings`.

## Final whole-branch review fixes — 2026-08-02

### Fixes

- Replaced Vite-only `import.meta.glob` with a generated static fixture registry. `apps/web/scripts/generate-fixture-modules.mjs` recursively enumerates fixture JSON files and writes explicit Next.js-compatible imports keyed as `./fixtures/<scenario>/<name>.json`.
- Kept fixture smoke coverage; generated keys resolve in `scenarios.test.ts`. Generator output is deterministic.
- Cast fixture literals at the `series.test.ts` boundary to the generated `PortfolioSeries` and `HoldingSeries` contracts.
- Consumed `useCancellableQuery`'s `loading` state in overview and holding-detail chart panels; removed the now-dead overview action-error reset.
- Narrowed persisted import-report loading to `SingleImportResult | null` and removed its redundant caller-side type guard.

### Validation

```text
npm --prefix apps/web test
Test Files  34 passed (34)
Tests       170 passed (170)
Exit code   0

npm --prefix apps/web run build
Next.js 15.5.22
Compiled successfully
Linting and checking validity of types completed
Exit code   0

node apps/web/scripts/generate-fixture-modules.mjs
fixture-modules.ts checksum unchanged across consecutive runs
Exit code   0
```
