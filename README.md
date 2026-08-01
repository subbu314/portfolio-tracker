# Portfolio Tracker

Local Zerodha equity + Coin MF tracker (Next.js + FastAPI + SQLite).

## Frontend ↔ API contract

- FastAPI schemas under `apps/api/src/portfolio_tracker/schemas/` are source of truth.
- Regenerate with `npm run generate:api`.
- That command writes `apps/web/openapi.json` and `apps/web/src/lib/api-types.ts` (commit both).
- Browser → API direct via `NEXT_PUBLIC_API_URL` (default `http://127.0.0.1:8000`); CORS allows `http://localhost:3000`.
