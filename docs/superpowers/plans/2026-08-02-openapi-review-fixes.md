# OpenAPI Review Fixes + Web Fat Trim Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the three Important review findings on `feat/portfolio-tracker-v1` (fixed-key window typings, OpenAPI/TS artifact drift guards, handwritten client request coverage) and strip create-next-app scaffold fat from `apps/web`.

**Architecture:** Keep FastAPI Pydantic schemas as the single HTTP contract. Replace `dict[WindowKey, …]` with an explicit `WindowsMap` model so OpenAPI emits required `ITD`/`1Y`/`3Y`/`5Y` properties and `openapi-typescript` generates named fields. Add cheap drift checks (committed `openapi.json` vs live app; regenerated `api-types.ts` vs committed). Expand Vitest to table-drive every `api.*` method’s method/URL/headers/body. Delete unused Next scaffold assets and unused web test deps — do **not** re-run the already-merged API fat-trim plan (`2026-08-01-fat-trim.md` / PR #3).

**Tech Stack:** FastAPI, Pydantic v2, pytest, `uv`; Next.js 15, TypeScript, `openapi-typescript`, Vitest, npm.

## Global Constraints

- Do **not** rename existing JSON field names (`ITD`, `1Y`, `3Y`, `5Y`, rates as fractions, excess as pp)
- Secrets never committed; never copy `.env` into docs or fixtures
- `CORS_ORIGINS` default stays `http://localhost:3000`; client default base URL `http://127.0.0.1:8000`
- Services may keep returning plain `dict` — routers validate via `response_model`
- Do **not** hand-edit `apps/web/src/lib/api-types.ts` or `apps/web/openapi.json` — regenerate via `npm run generate:api`
- Every API task ends green: `cd apps/api && uv run pytest -q`
- Every web task ends green: `cd apps/web && npm test`
- Prefer edit over rewrite; YAGNI — no GitHub Actions workflow unless already present (none today)
- Out of scope: re-auditing API modules for leftover fat from PR #3; UI pages from portfolio-tracker plan Tasks 12–16

## File Structure

```
apps/api/src/portfolio_tracker/schemas/
  common.py                 # Task 1: add WindowsMap
  portfolio.py              # Task 1: windows: WindowsMap

apps/api/tests/
  test_schemas_common.py    # Task 1: WindowsMap round-trip + aliases
  test_openapi_portfolio.py # Task 1: assert OpenAPI windows properties
  test_openapi_export.py    # Task 2: committed openapi.json drift check

apps/web/
  openapi.json              # Task 1–2: regenerate, never hand-edit
  src/lib/api-types.ts      # Task 1–2: regenerate, never hand-edit
  src/lib/api.ts            # unchanged API surface (Task 3 tests it)
  src/__tests__/api.test.ts # Task 3: table-driven request coverage
  package.json              # Task 2 + 4: check:api script; drop unused deps
  vitest.config.ts          # Task 4: node env (drop jsdom)
  README.md                 # Task 4: lean project readme
  src/app/layout.tsx        # Task 4: drop Geist / Create Next App metadata
  src/app/globals.css       # Task 4: minimal reset
  src/app/page.module.css   # Task 4: DELETE (unused)
  public/*.svg              # Task 4: DELETE unused scaffold SVGs
```

---

### Task 1: Fixed-key `WindowsMap` in OpenAPI + regenerated TS

**Files:**
- Modify: `apps/api/src/portfolio_tracker/schemas/common.py`
- Modify: `apps/api/src/portfolio_tracker/schemas/portfolio.py`
- Modify: `apps/api/tests/test_schemas_common.py`
- Modify: `apps/api/tests/test_openapi_portfolio.py`
- Regenerate: `apps/web/openapi.json`, `apps/web/src/lib/api-types.ts`

**Interfaces:**
- Consumes: existing `WindowMetrics`, `WindowKey`; service dicts shaped `{"ITD": …, "1Y": …, "3Y": …, "5Y": …}`
- Produces: `WindowsMap` with required nullable properties serialized under JSON keys `ITD`, `1Y`, `3Y`, `5Y`; portfolio schemas use `windows: WindowsMap`

- [ ] **Step 1: Write failing tests**

Append to `apps/api/tests/test_schemas_common.py`:

```python
from portfolio_tracker.schemas.common import AbsoluteReturn, WindowMetrics, WindowsMap


def test_windows_map_round_trip_preserves_json_keys():
    raw = {
        "ITD": {
            "absolute_pct": 0.1,
            "absolute_inr": 10.0,
            "xirr": None,
            "cagr": None,
            "benchmark_return": None,
            "absolute_excess_pp": None,
            "xirr_excess_pp": None,
            "cagr_excess_pp": None,
        },
        "1Y": None,
        "3Y": None,
        "5Y": None,
    }
    model = WindowsMap.model_validate(raw)
    dumped = model.model_dump(by_alias=True)
    assert set(dumped.keys()) == {"ITD", "1Y", "3Y", "5Y"}
    assert dumped["ITD"]["absolute_pct"] == 0.1
    assert dumped["1Y"] is None
```

Append to `apps/api/tests/test_openapi_portfolio.py`:

```python
def test_openapi_windows_map_has_fixed_properties():
    schema = TestClient(create_app()).get("/openapi.json").json()
    windows = schema["components"]["schemas"]["WindowsMap"]
    props = set(windows["properties"].keys())
    assert props == {"ITD", "1Y", "3Y", "5Y"}
    assert set(windows["required"]) == {"ITD", "1Y", "3Y", "5Y"}
    assert windows.get("additionalProperties") is False

    overview_windows = schema["components"]["schemas"]["OverviewResponse"]["properties"][
        "windows"
    ]
    assert overview_windows.get("$ref") == "#/components/schemas/WindowsMap"
```

Keep existing tests in both files.

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd apps/api && uv run pytest tests/test_schemas_common.py::test_windows_map_round_trip_preserves_json_keys tests/test_openapi_portfolio.py::test_openapi_windows_map_has_fixed_properties -v
```

Expected: FAIL (`WindowsMap` not defined / schema missing).

- [ ] **Step 3: Implement `WindowsMap` and wire portfolio schemas**

In `apps/api/src/portfolio_tracker/schemas/common.py`, add (keep existing models; add `Field` import):

```python
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ... existing RequestTokenBody, AbsoluteReturn, WindowKey, WindowMetrics, AllocationSlice ...


class WindowsMap(BaseModel):
    """Fixed window keys so OpenAPI/TS keep named properties (not string index)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    ITD: WindowMetrics | None
    y1: WindowMetrics | None = Field(alias="1Y")
    y3: WindowMetrics | None = Field(alias="3Y")
    y5: WindowMetrics | None = Field(alias="5Y")
```

In `apps/api/src/portfolio_tracker/schemas/portfolio.py`, import `WindowsMap` and replace every `windows: dict[WindowKey, WindowMetrics | None]` with `windows: WindowsMap` on `HoldingResponse`, `OverviewResponse`, and `ContributorResponse`. Keep `windows_available: list[WindowKey]` and `default_window: WindowKey` on `PerformanceResponse`.

- [ ] **Step 4: Run API tests**

Run:

```bash
cd apps/api && uv run pytest tests/test_schemas_common.py tests/test_openapi_portfolio.py tests/test_api_integration.py tests/test_portfolio.py -q
```

Expected: PASS (integration payloads already include all four window keys).

- [ ] **Step 5: Regenerate OpenAPI + TS types**

Run from repo root:

```bash
npm run generate:api
```

Expected: rewrites `apps/web/openapi.json` and `apps/web/src/lib/api-types.ts`. Spot-check generated windows shape is named keys, e.g.:

```ts
windows: {
  ITD: components["schemas"]["WindowMetrics"] | null;
  "1Y": components["schemas"]["WindowMetrics"] | null;
  "3Y": components["schemas"]["WindowMetrics"] | null;
  "5Y": components["schemas"]["WindowMetrics"] | null;
};
```

Not `{ [key: string]: … }`.

- [ ] **Step 6: Commit**

```bash
git add \
  apps/api/src/portfolio_tracker/schemas/common.py \
  apps/api/src/portfolio_tracker/schemas/portfolio.py \
  apps/api/tests/test_schemas_common.py \
  apps/api/tests/test_openapi_portfolio.py \
  apps/web/openapi.json \
  apps/web/src/lib/api-types.ts
git commit -m "$(cat <<'EOF'
fix(api): emit fixed-key WindowsMap in OpenAPI for typed windows

EOF
)"
```

---

### Task 2: Artifact drift guards

**Files:**
- Modify: `apps/api/tests/test_openapi_export.py`
- Modify: `apps/web/package.json` (add `check:api` script)
- Modify: `package.json` (root — wire `check:api` into `test` or document; prefer add `npm run check:api` and call it from root `test`)

**Interfaces:**
- Consumes: `create_app().openapi()`, committed `apps/web/openapi.json`, `openapi-typescript` CLI
- Produces: pytest that fails when committed OpenAPI drifts; npm script that fails when committed `api-types.ts` drifts from regeneration

- [ ] **Step 1: Write failing OpenAPI drift test**

Replace/extend `apps/api/tests/test_openapi_export.py` to:

```python
import json
from pathlib import Path

from portfolio_tracker.main import create_app

OPENAPI_PATH = Path(__file__).resolve().parents[2] / "web" / "openapi.json"


def test_openapi_document_is_valid_json_with_paths():
    doc = create_app().openapi()
    assert doc["openapi"].startswith("3.")
    assert "/portfolio/overview" in doc["paths"]
    assert "/import/csv" in doc["paths"]
    assert "/sync" in doc["paths"]
    raw = json.dumps(doc)
    assert json.loads(raw)["info"]["title"] == "Portfolio Tracker API"


def test_committed_openapi_matches_live_app():
    live = create_app().openapi()
    committed = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
    assert committed == live, (
        "apps/web/openapi.json is stale. From repo root run: npm run generate:api"
    )
```

Path note: `tests/` → `apps/api` is `parents[1]`; `apps` is `parents[2]`; so `parents[2] / "web" / "openapi.json"` is correct for `apps/web/openapi.json`.

- [ ] **Step 2: Prove the drift test can fail**

Temporarily break the assertion path by editing one key in a copy — or run after intentionally skipping regeneration from Task 1. Prefer: briefly mutate committed file in a throwaway way only if Task 1 artifacts were not regenerated; if Task 1 already regenerated, force fail once:

```bash
cd apps/api && uv run pytest tests/test_openapi_export.py::test_committed_openapi_matches_live_app -v
```

If Task 1 committed matching artifacts: PASS already. To verify failure mode, change live title expectation is wrong approach — instead temporarily rename a path in the committed file, run test (expect FAIL), restore via `git checkout -- apps/web/openapi.json`.

- [ ] **Step 3: Add `check:api` for TypeScript types drift**

In `apps/web/package.json` scripts, add:

```json
"check:api": "openapi-typescript ./openapi.json -o ./src/lib/api-types.check.ts && node -e \"const fs=require('fs');const a=fs.readFileSync('src/lib/api-types.ts','utf8');const b=fs.readFileSync('src/lib/api-types.check.ts','utf8');fs.unlinkSync('src/lib/api-types.check.ts');if(a!==b){console.error('api-types.ts is stale; run npm run generate:api from repo root');process.exit(1)}\""
```

In root `package.json`, update scripts:

```json
"check:api": "npm run generate:openapi && npm --prefix apps/web run check:api",
"test": "npm run api:test && npm run check:api && npm run web:test"
```

Note: root `check:api` re-exports OpenAPI then verifies TS. API pytest already guards committed JSON vs live app — order in `test` keeps API unit/integration first, then artifact check, then web tests.

Do **not** add a GitHub Actions workflow in this plan (YAGNI until CI exists).

- [ ] **Step 4: Run drift checks green**

```bash
cd apps/api && uv run pytest tests/test_openapi_export.py -v
npm run check:api
npm test
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/tests/test_openapi_export.py apps/web/package.json package.json
git commit -m "$(cat <<'EOF'
test: fail when OpenAPI or api-types artifacts drift

EOF
)"
```

---

### Task 3: Table-driven coverage for handwritten `api` methods

**Files:**
- Modify: `apps/web/src/__tests__/api.test.ts`

**Interfaces:**
- Consumes: `api` from `apps/web/src/lib/api.ts` (methods listed below)
- Produces: tests asserting method, URL, headers, and body shape for every client method

Methods to cover (from `api.ts`):

| Method | HTTP | Path pattern | Body / notes |
|--------|------|--------------|--------------|
| `getHealth` | GET | `/health` | — |
| `getOverview` | GET | `/portfolio/overview` | — |
| `getHoldings` | GET | `/portfolio/holdings` | unwraps `.holdings` |
| `getPerformance` | GET | `/portfolio/performance` | — |
| `getAlerts` | GET | `/portfolio/alerts` | — |
| `getAuthStatus` | GET | `/auth/status` | — |
| `getLoginUrl` | GET | `/auth/login-url` | — |
| `postCallback` | POST | `/auth/callback` | JSON `{ request_token }` |
| `postLogout` | POST | `/auth/logout` | no body |
| `postSync` | POST | `/sync` | no body |
| `postImportCsv` | POST | `/import/csv` | FormData field `file` |
| `postImportCsvBatch` | POST | `/import/csv` | FormData field `files` (multi) |
| `getBenchmarkSettings` | GET | `/settings/benchmarks` | — |
| `putBenchmark` | PUT | `/settings/benchmarks/{id}` | JSON `{ benchmark_index }` |
| `putCategory` | PUT | `/settings/categories/{id}` | JSON `{ category }` |

Keep the existing non-OK throw test.

- [ ] **Step 1: Rewrite `api.test.ts` with table-driven cases**

Replace `apps/web/src/__tests__/api.test.ts` with:

```typescript
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/lib/api";

const BASE = "http://127.0.0.1:8000";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function mockOk(json: unknown = {}) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => json,
    text: async () => "",
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("api client request mapping", () => {
  it("getHealth GETs /health", async () => {
    const fetchMock = mockOk({ status: "ok" });
    await api.getHealth();
    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE}/health`,
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("getOverview GETs /portfolio/overview", async () => {
    const fetchMock = mockOk({
      as_of: "2026-08-01",
      total_value: 100,
      absolute: {
        gain_inr: 10,
        gain_pct: 0.1,
        invested_cost: 90,
        current_value: 100,
      },
      xirr: null,
      cagr: null,
      benchmark_return: null,
      absolute_excess_pp: null,
      xirr_excess_pp: null,
      cagr_excess_pp: null,
      allocation: [],
      incomplete: false,
      windows: { ITD: null, "1Y": null, "3Y": null, "5Y": null },
    });
    const result = await api.getOverview();
    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE}/portfolio/overview`,
      expect.objectContaining({ cache: "no-store" }),
    );
    expect(result.total_value).toBe(100);
  });

  it("getHoldings unwraps holdings array", async () => {
    const fetchMock = mockOk({ holdings: [{ symbol: "A" }] });
    const rows = await api.getHoldings();
    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE}/portfolio/holdings`,
      expect.objectContaining({ cache: "no-store" }),
    );
    expect(rows).toEqual([{ symbol: "A" }]);
  });

  it.each([
    ["getPerformance", () => api.getPerformance(), "/portfolio/performance"],
    ["getAlerts", () => api.getAlerts(), "/portfolio/alerts"],
    ["getAuthStatus", () => api.getAuthStatus(), "/auth/status"],
    ["getLoginUrl", () => api.getLoginUrl(), "/auth/login-url"],
    ["getBenchmarkSettings", () => api.getBenchmarkSettings(), "/settings/benchmarks"],
  ] as const)("%s GETs %s", async (_name, call, path) => {
    const fetchMock = mockOk({});
    await call();
    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE}${path}`,
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("postCallback POSTs JSON request_token", async () => {
    const fetchMock = mockOk({ connected: true });
    await api.postCallback("tok-1");
    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE}/auth/callback`,
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request_token: "tok-1" }),
        cache: "no-store",
      }),
    );
  });

  it("postLogout POSTs /auth/logout", async () => {
    const fetchMock = mockOk({ connected: false });
    await api.postLogout();
    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE}/auth/logout`,
      expect.objectContaining({ method: "POST", cache: "no-store" }),
    );
  });

  it("postSync POSTs /sync", async () => {
    const fetchMock = mockOk({});
    await api.postSync();
    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE}/sync`,
      expect.objectContaining({ method: "POST", cache: "no-store" }),
    );
  });

  it("postImportCsv sends multipart file field", async () => {
    const fetchMock = mockOk({
      format: "console_tradebook",
      new: 1,
      existing: 0,
      segment_counts: {},
      flagged_rows: [],
      date_min: null,
      date_max: null,
      financial_years: [],
    });
    const file = new File(["symbol,trade_date\n"], "eq.csv", { type: "text/csv" });
    await api.postImportCsv(file);
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(fetchMock.mock.calls[0][0]).toBe(`${BASE}/import/csv`);
    expect(init.method).toBe("POST");
    expect(init.body).toBeInstanceOf(FormData);
    expect((init.body as FormData).get("file")).toBeTruthy();
  });

  it("postImportCsvBatch appends files field", async () => {
    const fetchMock = mockOk({});
    const f1 = new File(["a"], "a.csv", { type: "text/csv" });
    const f2 = new File(["b"], "b.csv", { type: "text/csv" });
    await api.postImportCsvBatch([f1, f2]);
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(fetchMock.mock.calls[0][0]).toBe(`${BASE}/import/csv`);
    expect(init.method).toBe("POST");
    const body = init.body as FormData;
    expect(body.getAll("files")).toHaveLength(2);
  });

  it("putBenchmark PUTs JSON benchmark_index", async () => {
    const fetchMock = mockOk({});
    await api.putBenchmark(9, "NIFTY 50");
    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE}/settings/benchmarks/9`,
      expect.objectContaining({
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ benchmark_index: "NIFTY 50" }),
        cache: "no-store",
      }),
    );
  });

  it("putCategory PUTs JSON category", async () => {
    const fetchMock = mockOk({});
    await api.putCategory(9, "Large Cap");
    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE}/settings/categories/9`,
      expect.objectContaining({
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category: "Large Cap" }),
        cache: "no-store",
      }),
    );
  });

  it("throws with response text on non-OK", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        statusText: "Bad Request",
        text: async () => "nope",
      }),
    );
    await expect(api.getHealth()).rejects.toThrow(/nope/);
  });
});
```

- [ ] **Step 2: Run web tests**

```bash
cd apps/web && npm test
```

Expected: PASS (all cases green). If `File` / `FormData` missing under Vitest node env after Task 4, keep Task 3 on current env first; Task 4 may switch to `environment: "node"` and must keep these tests passing (Node 18+ has `File`/`FormData`).

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/__tests__/api.test.ts
git commit -m "$(cat <<'EOF'
test(web): cover all api client request mappings

EOF
)"
```

---

### Task 4: Trim `apps/web` scaffold fat

**Files:**
- Delete: `apps/web/public/file.svg`, `apps/web/public/globe.svg`, `apps/web/public/next.svg`, `apps/web/public/vercel.svg`, `apps/web/public/window.svg`
- Delete: `apps/web/src/app/page.module.css`
- Modify: `apps/web/src/app/layout.tsx`
- Modify: `apps/web/src/app/globals.css`
- Modify: `apps/web/README.md`
- Modify: `apps/web/package.json` (remove unused deps)
- Modify: `apps/web/vitest.config.ts` (node environment)
- Modify: `apps/web/src/app/page.tsx` only if needed after layout change (keep placeholder)

**Interfaces:**
- Consumes: existing placeholder page + vitest tests from Task 3
- Produces: lean web package without create-next-app marketing assets / unused test libraries

- [ ] **Step 1: Delete unused scaffold files**

```bash
rm -f \
  apps/web/public/file.svg \
  apps/web/public/globe.svg \
  apps/web/public/next.svg \
  apps/web/public/vercel.svg \
  apps/web/public/window.svg \
  apps/web/src/app/page.module.css
```

`public/` may be empty afterward — leave the directory (or omit); do not add placeholder assets.

- [ ] **Step 2: Slim layout + CSS + README**

Replace `apps/web/src/app/layout.tsx` with:

```tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Portfolio Tracker",
  description: "Local Zerodha equity + Coin MF tracker",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
```

Replace `apps/web/src/app/globals.css` with:

```css
*,
*::before,
*::after {
  box-sizing: border-box;
}

html,
body {
  margin: 0;
  padding: 0;
  font-family: ui-sans-serif, system-ui, sans-serif;
}
```

Replace `apps/web/README.md` with exactly:

````markdown
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
````

- [ ] **Step 3: Drop unused deps and switch Vitest to node**

In `apps/web/package.json`, remove these `devDependencies` if present:

- `@testing-library/jest-dom`
- `@testing-library/react`
- `jsdom`
- `@vitejs/plugin-react`

Keep: `vitest`, `typescript`, `openapi-typescript`, eslint packages, `@types/*`.

Replace `apps/web/vitest.config.ts` with:

```ts
import path from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

Then refresh lockfile:

```bash
cd apps/web && npm install
```

- [ ] **Step 4: Verify**

```bash
cd apps/web && npm test
cd apps/web && npx tsc --noEmit
npm test
```

Expected: all PASS; typecheck clean; no imports of deleted CSS/SVGs.

- [ ] **Step 5: Commit**

```bash
git add -A apps/web package.json
git status
git commit -m "$(cat <<'EOF'
chore(web): strip create-next-app scaffold fat

EOF
)"
```

Only stage intentional paths (do not add `.env`). If root `package.json` was already committed in Task 2, this commit may only touch `apps/web`.

---

## Self-Review

**1. Spec / review coverage**

| Review finding | Task |
|----------------|------|
| Window keys lose generated type safety | Task 1 |
| Generated artifacts lack drift protection | Task 2 |
| Handwritten request mappings untested | Task 3 |
| Trim fat (web scaffold; API fat-trim already done) | Task 4 |

**2. Placeholder scan:** No TBD/TODO steps; commands and code are complete.

**3. Type consistency:** JSON keys stay `ITD`/`1Y`/`3Y`/`5Y` via aliases; TS regeneration expected to use those names; client tests use the same keys in overview fixture.

**Out of scope confirmed:** API module re-trim from `2026-08-01-fat-trim.md`; GitHub Actions CI; UI pages.
