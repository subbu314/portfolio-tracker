# Portfolio Tracker Web

Next.js App Router shell. Typed API client lives in `src/lib/api.ts` (types from OpenAPI).

## Commands

```bash
npm run dev          # http://localhost:3000
npm test             # vitest
npm run generate:api # from openapi.json → src/lib/api-types.ts
npm run check:api    # fail if api-types.ts stale vs openapi.json
```

Regenerate both OpenAPI snapshot and types from repo root: `npm run generate:api`.

Browser calls `NEXT_PUBLIC_API_URL` (default `http://127.0.0.1:8000`).

## Local mock scenarios

Set `NEXT_PUBLIC_USE_MOCKS=true` to enable local MSW scenarios and switch scenarios from the development picker. Leave it unset to call the live API.
