# OpenAPI Contract + Typed Web Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make FastAPI the single HTTP contract (Pydantic response models → OpenAPI) and generate TypeScript types for a thin Next.js fetch client (browser → API via CORS).

**Architecture:** Add Pydantic response schemas under `apps/api/src/portfolio_tracker/schemas/`, attach them as `response_model` on every router. Export `openapi.json` from the app factory (no live server required). Scaffold minimal `apps/web` if missing, generate `api-types.ts` with `openapi-typescript`, wrap paths in `lib/api.ts`. Browser calls `http://127.0.0.1:8000` directly; CORS already allows `http://localhost:3000`. No Next.js BFF. No hand-maintained OpenAPI YAML. No Orval.

**Tech Stack:** FastAPI, Pydantic v2, pytest, httpx/TestClient; Next.js 15 App Router + TypeScript; `openapi-typescript`; Vitest.

## Global Constraints

- **Do not rename** existing JSON field names (frontend + integration tests depend on them)
- Rates remain fractions; excess remains percentage points
- Secrets never committed; never copy `.env` into docs or fixtures
- `CORS_ORIGINS` default stays `http://localhost:3000`; client default base URL `http://127.0.0.1:8000`
- This plan **supersedes** hand-written `apps/web/src/lib/types.ts` from `2026-08-01-portfolio-tracker.md` Task 12 — UI pages still come from that plan after this client exists
- Every API task ends green: `cd apps/api && uv run pytest -q`
- Every web task ends green: `cd apps/web && npm test`
- Prefer edit over rewrite; services may keep returning `dict` — routers validate via `response_model`

## File Structure

```
apps/api/src/portfolio_tracker/
  schemas/
    common.py              # keep RequestTokenBody; add AbsoluteReturn, WindowMetrics, etc.
    portfolio.py           # Overview, Holdings, Performance, Alerts
    auth.py                # LoginUrl, Connected, AuthStatus
    sync.py                # SyncResponse + PricesRefresh
    settings.py            # Benchmark list/update, Category update
    import_.py             # ImportResult, BatchImportResult, error detail
  routers/*.py             # add response_model=...
  scripts/export_openapi.py  # OR apps/api/scripts/export_openapi.py

apps/web/                    # create if missing (minimal scaffold)
  openapi.json               # generated + committed
  package.json               # scripts: generate:api, test, dev
  src/lib/api-types.ts       # generated — do not hand-edit
  src/lib/api.ts             # thin typed fetch wrapper
  src/lib/format.ts          # INR / % / pp helpers (needed by later UI)
  src/__tests__/api.test.ts
  src/__tests__/format.test.ts
  src/app/page.tsx           # placeholder proving client import compiles

package.json (root)          # add generate:api script
```

---

### Task 1: Shared metric / window Pydantic models

**Files:**
- Modify: `apps/api/src/portfolio_tracker/schemas/common.py`
- Create: `apps/api/tests/test_schemas_common.py`

**Interfaces:**
- Consumes: existing `RequestTokenBody`
- Produces: `AbsoluteReturn`, `WindowKey`, `WindowMetrics`, `AllocationSlice` used by later schema modules

- [ ] **Step 1: Write failing import test**

```python
# apps/api/tests/test_schemas_common.py
from portfolio_tracker.schemas.common import AbsoluteReturn, WindowMetrics


def test_absolute_return_round_trip():
    model = AbsoluteReturn(
        gain_inr=100.0,
        gain_pct=0.1,
        invested_cost=1000.0,
        current_value=1100.0,
    )
    assert model.model_dump()["gain_pct"] == 0.1


def test_window_metrics_allows_nulls():
    model = WindowMetrics(
        absolute_pct=None,
        absolute_inr=None,
        xirr=None,
        cagr=None,
        benchmark_return=None,
        absolute_excess_pp=None,
        xirr_excess_pp=None,
        cagr_excess_pp=None,
    )
    assert model.xirr is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && uv run pytest tests/test_schemas_common.py -v`

Expected: FAIL with `ImportError` / `cannot import name 'AbsoluteReturn'`

- [ ] **Step 3: Implement shared schemas**

Replace/extend `apps/api/src/portfolio_tracker/schemas/common.py` to:

```python
from typing import Literal

from pydantic import BaseModel, ConfigDict


class RequestTokenBody(BaseModel):
    request_token: str


class AbsoluteReturn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gain_inr: float
    gain_pct: float | None
    invested_cost: float
    current_value: float


WindowKey = Literal["ITD", "1Y", "3Y", "5Y"]


class WindowMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    absolute_pct: float | None = None
    absolute_inr: float | None = None
    xirr: float | None = None
    cagr: float | None = None
    benchmark_return: float | None = None
    absolute_excess_pp: float | None = None
    xirr_excess_pp: float | None = None
    cagr_excess_pp: float | None = None


class AllocationSlice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    weight: float
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/api && uv run pytest tests/test_schemas_common.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/portfolio_tracker/schemas/common.py apps/api/tests/test_schemas_common.py
git commit -m "feat(api): add shared AbsoluteReturn and WindowMetrics schemas"
```

---

### Task 2: Portfolio response schemas + router `response_model`

**Files:**
- Create: `apps/api/src/portfolio_tracker/schemas/portfolio.py`
- Modify: `apps/api/src/portfolio_tracker/routers/portfolio.py`
- Create: `apps/api/tests/test_openapi_portfolio.py`
- Test (existing must stay green): `apps/api/tests/test_api_integration.py`, `apps/api/tests/test_portfolio.py`

**Interfaces:**
- Consumes: `AbsoluteReturn`, `WindowMetrics`, `WindowKey`, `AllocationSlice` from Task 1
- Produces: `OverviewResponse`, `HoldingsResponse`, `HoldingResponse`, `PerformanceResponse`, `AlertsResponse`; OpenAPI components for those names

- [ ] **Step 1: Write failing OpenAPI component test**

```python
# apps/api/tests/test_openapi_portfolio.py
from fastapi.testclient import TestClient

from portfolio_tracker.main import create_app


def test_openapi_includes_portfolio_response_schemas():
    schema = TestClient(create_app()).get("/openapi.json").json()
    components = schema["components"]["schemas"]
    for name in (
        "OverviewResponse",
        "HoldingsResponse",
        "HoldingResponse",
        "PerformanceResponse",
        "AlertsResponse",
        "WindowMetrics",
        "AbsoluteReturn",
    ):
        assert name in components, name

    overview_path = schema["paths"]["/portfolio/overview"]["get"]
    assert "OverviewResponse" in overview_path["responses"]["200"]["content"]["application/json"]["schema"].get(
        "$ref", ""
    ) or overview_path["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/OverviewResponse"
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && uv run pytest tests/test_openapi_portfolio.py -v`

Expected: FAIL — schemas missing from OpenAPI components

- [ ] **Step 3: Add portfolio schemas**

Create `apps/api/src/portfolio_tracker/schemas/portfolio.py`:

```python
from portfolio_tracker.schemas.common import (
    AbsoluteReturn,
    AllocationSlice,
    WindowKey,
    WindowMetrics,
)


class HoldingResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    instrument_id: int
    symbol: str
    instrument_type: str
    qty: float
    avg_price: float
    ltp: float | None
    value: float | None
    absolute_pct: float | None
    absolute_inr: float | None
    xirr: float | None
    cagr: float | None
    benchmark: str
    benchmark_return: float | None
    absolute_excess_pp: float | None
    xirr_excess_pp: float | None
    cagr_excess_pp: float | None
    incomplete: bool
    needs_category: bool
    windows: dict[WindowKey, WindowMetrics | None]


class HoldingsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    holdings: list[HoldingResponse]


class OverviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of: str
    total_value: float
    absolute: AbsoluteReturn
    xirr: float | None
    cagr: float | None
    benchmark_return: float | None
    absolute_excess_pp: float | None
    xirr_excess_pp: float | None
    cagr_excess_pp: float | None
    allocation: list[AllocationSlice]
    incomplete: bool
    windows: dict[WindowKey, WindowMetrics | None]


class ContributorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    absolute_excess_pp: float | None
    xirr_excess_pp: float | None
    cagr_excess_pp: float | None
    value: float | None
    weight: float
    windows: dict[WindowKey, WindowMetrics | None]


class PerformanceResponse(OverviewResponse):
    contributors: list[ContributorResponse]
    holdings: list[HoldingResponse]
    windows_available: list[WindowKey]
    default_window: WindowKey


class ReconcileDiff(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instrument_id: int
    symbol: str
    holdings_qty: float
    tx_qty: float
    delta: float


class GapAlert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    suggested_from: str
    suggested_to: str
    message: str


class AlertsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token_connected: bool
    credentials_configured: bool
    reconcile: list[ReconcileDiff]
    reconcile_message: str | None = None
    gap: GapAlert | None
```

- [ ] **Step 4: Wire portfolio router**

Replace `apps/api/src/portfolio_tracker/routers/portfolio.py` with:

```python
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from portfolio_tracker.db.session import get_db
from portfolio_tracker.modules import portfolio, reconcile
from portfolio_tracker.schemas.portfolio import (
    AlertsResponse,
    HoldingsResponse,
    OverviewResponse,
    PerformanceResponse,
)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/overview", response_model=OverviewResponse)
def overview(session: Annotated[Session, Depends(get_db)]) -> dict:
    return portfolio.get_overview(session, as_of=date.today().isoformat())


@router.get("/holdings", response_model=HoldingsResponse)
def holdings(session: Annotated[Session, Depends(get_db)]) -> dict:
    rows = portfolio.get_holdings(session, as_of=date.today().isoformat())
    return {"holdings": rows}


@router.get("/alerts", response_model=AlertsResponse)
def alerts(session: Annotated[Session, Depends(get_db)]) -> dict:
    return reconcile.get_alerts(session, today=date.today().isoformat())


@router.get("/performance", response_model=PerformanceResponse)
def performance(session: Annotated[Session, Depends(get_db)]) -> dict:
    return portfolio.get_performance(session, as_of=date.today().isoformat())
```

Note: `extra="ignore"` on `HoldingResponse` so accidental internal keys never break responses; public fields stay locked.

- [ ] **Step 5: Run OpenAPI + integration tests**

Run:

```bash
cd apps/api && uv run pytest tests/test_openapi_portfolio.py tests/test_api_integration.py tests/test_portfolio.py -v
```

Expected: all PASS. If validation errors appear (e.g. windows keys), fix schema to match live payloads — do **not** change service field names.

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/portfolio_tracker/schemas/portfolio.py \
  apps/api/src/portfolio_tracker/routers/portfolio.py \
  apps/api/tests/test_openapi_portfolio.py
git commit -m "feat(api): add portfolio OpenAPI response models"
```

---

### Task 3: Auth, health, sync, settings response schemas

**Files:**
- Create: `apps/api/src/portfolio_tracker/schemas/auth.py`
- Create: `apps/api/src/portfolio_tracker/schemas/sync.py`
- Create: `apps/api/src/portfolio_tracker/schemas/settings.py`
- Modify: `apps/api/src/portfolio_tracker/routers/auth.py`
- Modify: `apps/api/src/portfolio_tracker/routers/health.py`
- Modify: `apps/api/src/portfolio_tracker/routers/sync.py`
- Modify: `apps/api/src/portfolio_tracker/routers/settings.py`
- Create: `apps/api/tests/test_openapi_auth_sync_settings.py`

**Interfaces:**
- Consumes: existing request bodies `RequestTokenBody`, `BenchmarkBody`, `CategoryBody`
- Produces: `HealthResponse`, `LoginUrlResponse`, `ConnectedResponse`, `AuthStatusResponse`, `SyncResponse`, `BenchmarkListResponse`, `BenchmarkUpdateResponse`, `CategoryUpdateResponse`

- [ ] **Step 1: Write failing OpenAPI names test**

```python
# apps/api/tests/test_openapi_auth_sync_settings.py
from fastapi.testclient import TestClient

from portfolio_tracker.main import create_app


def test_openapi_includes_auth_sync_settings_schemas():
    components = TestClient(create_app()).get("/openapi.json").json()["components"]["schemas"]
    for name in (
        "HealthResponse",
        "LoginUrlResponse",
        "ConnectedResponse",
        "AuthStatusResponse",
        "SyncResponse",
        "PricesRefreshResponse",
        "BenchmarkListResponse",
        "BenchmarkItem",
        "BenchmarkUpdateResponse",
        "CategoryUpdateResponse",
    ):
        assert name in components, name
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && uv run pytest tests/test_openapi_auth_sync_settings.py -v`

Expected: FAIL

- [ ] **Step 3: Implement schemas**

`apps/api/src/portfolio_tracker/schemas/auth.py`:

```python
from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    status: str


class LoginUrlResponse(BaseModel):
    login_url: str


class ConnectedResponse(BaseModel):
    connected: bool


class AuthStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connected: bool
    credentials_configured: bool
    last_sync_at: str | None
    last_trade_append_at: str | None
```

`apps/api/src/portfolio_tracker/schemas/sync.py`:

```python
from pydantic import BaseModel, ConfigDict


class PricesRefreshResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    updated: int
    failed: list[str]
    incomplete: bool


class SyncResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    holdings_count: int
    trades_appended: int
    last_sync_at: str
    prices: PricesRefreshResponse
```

`apps/api/src/portfolio_tracker/schemas/settings.py`:

```python
from pydantic import BaseModel, ConfigDict


class BenchmarkItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instrument_id: int
    symbol: str
    instrument_type: str
    mf_category: str | None
    needs_category: bool
    benchmark_index: str
    source: str


class BenchmarkListResponse(BaseModel):
    items: list[BenchmarkItem]


class BenchmarkUpdateResponse(BaseModel):
    instrument_id: int
    benchmark_index: str
    source: str


class CategoryUpdateResponse(BaseModel):
    instrument_id: int
    mf_category: str | None
```

- [ ] **Step 4: Wire routers**

Health — set `response_model=HealthResponse`.

Auth — annotate:

```python
@router.get("/login-url", response_model=LoginUrlResponse)
...
@router.post("/callback", response_model=ConnectedResponse)
...
@router.get("/callback", response_model=ConnectedResponse)
...
@router.get("/status", response_model=AuthStatusResponse)
...
@router.post("/logout", response_model=ConnectedResponse)
```

Sync — `response_model=SyncResponse` on `POST /sync`.

Settings — move `BenchmarkBody` / `CategoryBody` into `schemas/settings.py` (or keep in router — prefer schemas file), then:

```python
@router.get("/benchmarks", response_model=BenchmarkListResponse)
...
@router.put("/benchmarks/{instrument_id}", response_model=BenchmarkUpdateResponse, ...)
...
@router.put("/categories/{instrument_id}", response_model=CategoryUpdateResponse, ...)
```

Import the models in each router; do not change status codes or error details.

- [ ] **Step 5: Run tests**

Run:

```bash
cd apps/api && uv run pytest tests/test_openapi_auth_sync_settings.py tests/test_api_integration.py tests/test_kite_auth.py tests/test_kite_sync.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/portfolio_tracker/schemas/auth.py \
  apps/api/src/portfolio_tracker/schemas/sync.py \
  apps/api/src/portfolio_tracker/schemas/settings.py \
  apps/api/src/portfolio_tracker/routers/auth.py \
  apps/api/src/portfolio_tracker/routers/health.py \
  apps/api/src/portfolio_tracker/routers/sync.py \
  apps/api/src/portfolio_tracker/routers/settings.py \
  apps/api/tests/test_openapi_auth_sync_settings.py
git commit -m "feat(api): add auth/sync/settings OpenAPI response models"
```

---

### Task 4: Import response schemas

**Files:**
- Create: `apps/api/src/portfolio_tracker/schemas/import_.py`
- Modify: `apps/api/src/portfolio_tracker/routers/import_.py`
- Create: `apps/api/tests/test_openapi_import.py`
- Test: `apps/api/tests/test_csv_import.py`, `apps/api/tests/test_api_integration.py`

**Interfaces:**
- Consumes: shapes from `csv_import.ImportResult` / `BatchImportResult` / `FileImportOk` / `FileImportErr`
- Produces: OpenAPI models covering both single-file and batch responses (union)

- [ ] **Step 1: Write failing OpenAPI test**

```python
# apps/api/tests/test_openapi_import.py
from fastapi.testclient import TestClient

from portfolio_tracker.main import create_app


def test_openapi_includes_import_schemas():
    components = TestClient(create_app()).get("/openapi.json").json()["components"]["schemas"]
    for name in (
        "ImportResultResponse",
        "BatchImportResultResponse",
        "FileImportOkResponse",
        "FileImportErrResponse",
        "ImportBadDetail",
    ):
        assert name in components, name
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && uv run pytest tests/test_openapi_import.py -v`

Expected: FAIL

- [ ] **Step 3: Implement import schemas**

```python
# apps/api/src/portfolio_tracker/schemas/import_.py
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ImportResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: Literal["console_tradebook"]
    new: int
    existing: int
    segment_counts: dict[str, int]
    flagged_rows: list[str]
    date_min: str | None
    date_max: str | None
    financial_years: list[str]


class FileImportOkResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str
    ok: Literal[True]
    format: Literal["console_tradebook"]
    new: int
    existing: int
    segment_counts: dict[str, int]
    flagged_rows: list[str]
    date_min: str | None
    date_max: str | None
    financial_years: list[str]


class FileImportErrResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str
    ok: Literal[False]
    code: Literal["encoding", "csv_format", "csv_parse", "empty"]
    message: str
    errors: list[str]
    action: str


class BatchImportResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    files: list[FileImportOkResponse | FileImportErrResponse]
    summary: dict[str, int]


class ImportBadDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str
    errors: list[str] = Field(default_factory=list)
    action: str


ImportCsvResponse = ImportResultResponse | BatchImportResultResponse
```

- [ ] **Step 4: Wire import router**

```python
from portfolio_tracker.schemas.import_ import ImportCsvResponse

@router.post(
    "/csv",
    response_model=ImportCsvResponse,
    responses={400: {"description": "Invalid CSV (single-file mode)"}},
)
async def import_csv_endpoint(...) -> dict:
    ...
```

Leave HTTPException `detail=` payloads as dicts (FastAPI error schema); optionally document `ImportBadDetail` under `responses={400: {"model": ImportBadDetail}}` if FastAPI version supports it — prefer:

```python
responses={400: {"model": ImportBadDetail}}
```

so OpenAPI includes the error shape.

- [ ] **Step 5: Run tests**

Run:

```bash
cd apps/api && uv run pytest tests/test_openapi_import.py tests/test_csv_import.py tests/test_api_integration.py -v
```

Expected: PASS. If union validation fails on batch vs single, ensure return values match TypedDicts exactly.

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/portfolio_tracker/schemas/import_.py \
  apps/api/src/portfolio_tracker/routers/import_.py \
  apps/api/tests/test_openapi_import.py
git commit -m "feat(api): add CSV import OpenAPI response models"
```

---

### Task 5: Export OpenAPI JSON script + full schema smoke test

**Files:**
- Create: `apps/api/scripts/export_openapi.py`
- Create: `apps/api/tests/test_openapi_export.py`
- Modify: root `package.json` (add `generate:openapi` helper that calls the script)

**Interfaces:**
- Consumes: `create_app().openapi()`
- Produces: stdout or file write of OpenAPI 3 document; later web task reads `apps/web/openapi.json`

- [ ] **Step 1: Write failing export test**

```python
# apps/api/tests/test_openapi_export.py
import json
from pathlib import Path

from portfolio_tracker.main import create_app


def test_openapi_document_is_valid_json_with_paths():
    doc = create_app().openapi()
    assert doc["openapi"].startswith("3.")
    assert "/portfolio/overview" in doc["paths"]
    assert "/import/csv" in doc["paths"]
    assert "/sync" in doc["paths"]
    # round-trip serializable
    raw = json.dumps(doc)
    assert json.loads(raw)["info"]["title"] == "Portfolio Tracker API"
```

- [ ] **Step 2: Run test — should PASS once Tasks 2–4 done**

Run: `cd apps/api && uv run pytest tests/test_openapi_export.py -v`

Expected: PASS (this locks the export surface)

- [ ] **Step 3: Add export script**

```python
# apps/api/scripts/export_openapi.py
"""Dump OpenAPI JSON for the web TypeScript generator.

Usage (from repo root):
  cd apps/api && uv run python scripts/export_openapi.py ../web/openapi.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from portfolio_tracker.main import create_app


def main(argv: list[str]) -> int:
    out = Path(argv[1]) if len(argv) > 1 else Path("-")
    doc = create_app().openapi()
    text = json.dumps(doc, indent=2, sort_keys=True) + "\n"
    if str(out) == "-":
        sys.stdout.write(text)
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"Wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 4: Smoke-run export to a temp path**

Run:

```bash
cd apps/api && uv run python scripts/export_openapi.py /tmp/portfolio-openapi.json && python -c "import json; d=json.load(open('/tmp/portfolio-openapi.json')); assert '/health' in d['paths']"
```

Expected: `Wrote /tmp/portfolio-openapi.json` and exit 0

- [ ] **Step 5: Add root script**

Update root `package.json` scripts:

```json
{
  "name": "portfolio-tracker",
  "private": true,
  "scripts": {
    "api": "cd apps/api && uv run uvicorn portfolio_tracker.main:app --reload --port 8000",
    "api:test": "cd apps/api && uv run pytest -v",
    "generate:openapi": "cd apps/api && uv run python scripts/export_openapi.py ../web/openapi.json",
    "web": "npm --prefix apps/web run dev",
    "web:test": "npm --prefix apps/web test",
    "generate:api": "npm run generate:openapi && npm --prefix apps/web run generate:api",
    "test": "npm run api:test && npm run web:test"
  }
}
```

(`apps/web` scripts land in Task 6; `generate:api` will fail until then — OK after Task 6.)

- [ ] **Step 6: Commit**

```bash
git add apps/api/scripts/export_openapi.py apps/api/tests/test_openapi_export.py package.json
git commit -m "chore(api): add OpenAPI JSON export script"
```

---

### Task 6: Scaffold Next.js + generate TypeScript types

**Files:**
- Create: `apps/web/**` (Next.js 15 App Router)
- Create: `apps/web/openapi.json` (via export)
- Create: `apps/web/src/lib/api-types.ts` (generated)
- Create: `apps/web/src/lib/format.ts`
- Create: `apps/web/src/__tests__/format.test.ts`
- Create: `apps/web/vitest.config.ts`
- Modify: `apps/web/package.json`

**Interfaces:**
- Consumes: `apps/web/openapi.json` from Task 5
- Produces: `paths` / `components` types in `api-types.ts`; `formatInr` / `formatPct` / `formatPp` / `formatXirr`

- [ ] **Step 1: Scaffold Next.js app**

Run from repo root (non-interactive):

```bash
cd apps && npx --yes create-next-app@15 web --typescript --eslint --app --src-dir --no-tailwind --import-alias "@/*" --use-npm --turbopack false
```

If `apps/web` already exists from a prior attempt, skip create-next-app and continue.

Then:

```bash
cd apps/web && npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom @vitejs/plugin-react openapi-typescript
```

- [ ] **Step 2: Write failing format test**

```typescript
// apps/web/src/__tests__/format.test.ts
import { describe, expect, it } from "vitest";
import { formatInr, formatPct, formatPp } from "@/lib/format";

describe("format", () => {
  it("formats INR", () => {
    expect(formatInr(1234.5)).toContain("1,235");
  });
  it("formats percent", () => {
    expect(formatPct(0.256)).toBe("25.60%");
  });
  it("formats NA", () => {
    expect(formatPct(null)).toBe("N/A");
  });
  it("formats excess pp", () => {
    expect(formatPp(5.2)).toBe("+5.20 pp");
  });
});
```

- [ ] **Step 3: Implement format helpers + vitest config**

```typescript
// apps/web/src/lib/format.ts
export function formatInr(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "N/A";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatPct(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "N/A";
  return `${(value * 100).toFixed(2)}%`;
}

export function formatPp(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "N/A";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)} pp`;
}

export function formatXirr(value: number | null | undefined): string {
  return formatPct(value);
}
```

```typescript
// apps/web/vitest.config.ts
import path from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

Add to `apps/web/package.json` scripts:

```json
{
  "test": "vitest run",
  "generate:api": "openapi-typescript ./openapi.json -o ./src/lib/api-types.ts"
}
```

- [ ] **Step 4: Export OpenAPI + generate types**

```bash
npm run generate:openapi
cd apps/web && npm run generate:api
```

Expected: `apps/web/openapi.json` and `apps/web/src/lib/api-types.ts` exist; `api-types.ts` contains `export interface paths` and `/portfolio/overview`.

- [ ] **Step 5: Run format tests**

Run: `cd apps/web && npm test`

Expected: format tests PASS (api client tests arrive in Task 7)

- [ ] **Step 6: Commit**

```bash
git add apps/web package.json
git commit -m "chore(web): scaffold Next.js and generate OpenAPI TypeScript types"
```

Do **not** hand-edit `api-types.ts`. Add a one-line header comment only if the generator allows a banner; otherwise leave file pristine and document regeneration in README later.

---

### Task 7: Typed fetch client (browser → FastAPI)

**Files:**
- Create: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/__tests__/api.test.ts`
- Modify: `apps/web/src/app/page.tsx` (placeholder import to prove types compile)

**Interfaces:**
- Consumes: `paths` from `api-types.ts`; `NEXT_PUBLIC_API_URL` (default `http://127.0.0.1:8000`)
- Produces: `api.getOverview`, `api.getHoldings`, `api.getPerformance`, `api.getAlerts`, `api.getAuthStatus`, `api.getLoginUrl`, `api.postCallback`, `api.postLogout`, `api.postSync`, `api.postImportCsv`, `api.postImportCsvBatch`, `api.getBenchmarkSettings`, `api.putBenchmark`, `api.putCategory`, `api.getHealth`

- [ ] **Step 1: Write failing client test**

```typescript
// apps/web/src/__tests__/api.test.ts
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/lib/api";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("api client", () => {
  it("getOverview GETs /portfolio/overview and returns JSON", async () => {
    const payload = {
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
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => payload,
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await api.getOverview();

    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/portfolio/overview",
      expect.objectContaining({ cache: "no-store" }),
    );
    expect(result.total_value).toBe(100);
  });

  it("postImportCsv sends multipart file field", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        format: "console_tradebook",
        new: 1,
        existing: 0,
        segment_counts: {},
        flagged_rows: [],
        date_min: null,
        date_max: null,
        financial_years: [],
      }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const file = new File(["symbol,trade_date\n"], "eq.csv", { type: "text/csv" });

    await api.postImportCsv(file);

    expect(fetchMock).toHaveBeenCalled();
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(init.body).toBeInstanceOf(FormData);
    expect((init.body as FormData).get("file")).toBeTruthy();
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

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/web && npm test -- src/__tests__/api.test.ts`

Expected: FAIL — `Cannot find module '@/lib/api'`

- [ ] **Step 3: Implement typed client**

```typescript
// apps/web/src/lib/api.ts
import type { paths } from "./api-types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

type AppJson<P extends keyof paths, M extends keyof paths[P]> =
  paths[P][M] extends { responses: { 200: { content: { "application/json": infer R } } } }
    ? R
    : never;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { ...init, cache: "no-store" });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || res.statusText);
  }
  return res.json() as Promise<T>;
}

export type Overview = AppJson<"/portfolio/overview", "get">;
export type HoldingsResponse = AppJson<"/portfolio/holdings", "get">;
export type Holding = HoldingsResponse["holdings"][number];
export type Performance = AppJson<"/portfolio/performance", "get">;
export type Alerts = AppJson<"/portfolio/alerts", "get">;
export type AuthStatus = AppJson<"/auth/status", "get">;
export type SyncResult = AppJson<"/sync", "post">;
export type ImportResult = AppJson<"/import/csv", "post">;
export type BenchmarkList = AppJson<"/settings/benchmarks", "get">;

export const api = {
  getHealth: () => request<AppJson<"/health", "get">>("/health"),
  getOverview: () => request<Overview>("/portfolio/overview"),
  getHoldings: async () => {
    const data = await request<HoldingsResponse>("/portfolio/holdings");
    return data.holdings;
  },
  getPerformance: () => request<Performance>("/portfolio/performance"),
  getAlerts: () => request<Alerts>("/portfolio/alerts"),
  getAuthStatus: () => request<AuthStatus>("/auth/status"),
  getLoginUrl: () => request<AppJson<"/auth/login-url", "get">>("/auth/login-url"),
  postCallback: (request_token: string) =>
    request<AppJson<"/auth/callback", "post">>("/auth/callback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ request_token }),
    }),
  postLogout: () =>
    request<AppJson<"/auth/logout", "post">>("/auth/logout", { method: "POST" }),
  postSync: () => request<SyncResult>("/sync", { method: "POST" }),
  postImportCsv: async (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<ImportResult>("/import/csv", { method: "POST", body });
  },
  postImportCsvBatch: async (files: File[]) => {
    const body = new FormData();
    for (const file of files) body.append("files", file);
    return request<ImportResult>("/import/csv", { method: "POST", body });
  },
  getBenchmarkSettings: () => request<BenchmarkList>("/settings/benchmarks"),
  putBenchmark: (instrumentId: number, benchmark_index: string) =>
    request<AppJson<"/settings/benchmarks/{instrument_id}", "put">>(
      `/settings/benchmarks/${instrumentId}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ benchmark_index }),
      },
    ),
  putCategory: (instrumentId: number, category: string) =>
    request<AppJson<"/settings/categories/{instrument_id}", "put">>(
      `/settings/categories/${instrumentId}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category }),
      },
    ),
};
```

If `AppJson` fails to resolve for path templates like `/settings/benchmarks/{instrument_id}`, check exact keys in `api-types.ts` and use those string literals verbatim.

Placeholder page (prove import):

```tsx
// apps/web/src/app/page.tsx
import { api } from "@/lib/api";

export default async function HomePage() {
  // Server Component fetch is fine for local; CORS unused on server.
  // If API is down during `next build`, keep this as a client stub instead:
  return (
    <main>
      <h1>Portfolio Tracker</h1>
      <p>API client ready. Run Sync / Import from Settings once UI lands.</p>
      <p>Base: {process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000"}</p>
    </main>
  );
}
```

Avoid calling `api.getOverview()` at build time unless API is up — keep page static as above; optional later.

- [ ] **Step 4: Run web tests**

Run: `cd apps/web && npm test`

Expected: format + api tests PASS

- [ ] **Step 5: Typecheck**

Run: `cd apps/web && npx tsc --noEmit`

Expected: exit 0. Fix any `AppJson` path key mismatches against generated `api-types.ts`.

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/lib/api.ts apps/web/src/__tests__/api.test.ts apps/web/src/app/page.tsx
git commit -m "feat(web): add typed fetch client from OpenAPI paths"
```

---

### Task 8: Regeneration workflow docs + end-to-end smoke

**Files:**
- Create: `README.md` at repo root if missing; otherwise modify with an “API types” section
- Modify: `.gitignore` only if generated junk appears (do **not** ignore `openapi.json` or `api-types.ts` — commit both)

**Interfaces:**
- Consumes: Tasks 1–7 deliverables
- Produces: documented `npm run generate:api` workflow; verified smoke checklist

- [ ] **Step 1: Add README section**

If `README.md` does not exist, create a minimal file. Content to write:

- Title: `# Portfolio Tracker`
- One-line blurb: local Zerodha equity + Coin MF tracker (Next.js + FastAPI + SQLite)
- Section `## Frontend ↔ API contract` stating:
  - FastAPI schemas under `apps/api/src/portfolio_tracker/schemas/` are source of truth
  - Regenerate with `npm run generate:api`
  - That command writes `apps/web/openapi.json` and `apps/web/src/lib/api-types.ts` (commit both)
  - Browser → API direct via `NEXT_PUBLIC_API_URL` (default `http://127.0.0.1:8000`); CORS allows `http://localhost:3000`

If README already exists, append only the contract section.- [ ] **Step 2: Full smoke**

```bash
cd apps/api && uv run pytest -q
npm run generate:api
cd apps/web && npm test && npx tsc --noEmit
```

Expected: all green.

Manual (optional, API running):

```bash
# terminal A
npm run api
# terminal B
curl -s http://127.0.0.1:8000/openapi.json | head -c 200
npm run web
```

Open `http://localhost:3000` — placeholder page loads without CORS errors in console when you later call the API from client components.

- [ ] **Step 3: Commit**

```bash
git add README.md apps/web/openapi.json apps/web/src/lib/api-types.ts
git commit -m "docs: document OpenAPI TypeScript regeneration workflow"
```

---

## Self-review (plan author)

1. **Spec coverage:** Approach B covered — Pydantic models, live OpenAPI, export, `openapi-typescript`, thin fetch client, CORS direct. Full dashboard UI deferred to portfolio-tracker Tasks 13–16 (types now from codegen, not hand `types.ts`).
2. **Placeholders:** None.
3. **Type consistency:** Client method names match superseded Task 12 list; response field names match current Python services (`absolute.gain_pct`, `windows.ITD`, etc.).
4. **Gaps closed:** Import union, sync nested `prices`, alerts `reconcile_message`, multipart batch — all modeled.

## Out of scope (do not do in this plan)

- Overview / Holdings / Performance / Settings UI pages
- Next.js rewrite proxy / BFF
- Orval / openapi-generator full SDKs
- Hand-written `openapi.yaml`
- Changing metric formulas or JSON field names
