# UI API Gaps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the FastAPI endpoints and OpenAPI/TS client surface the Portfolio Tracker UI needs that do not exist today: holding detail, transactions, absolute-return chart series (portfolio + holding), `mf_category` on holdings, and data-driven Settings catalogs.

**Architecture:** Keep metrics recomputed on read. Add focused helpers under `modules/portfolio/` (series + holding reads) and thin router/schema layers. Chart series for v1 are **absolute cumulative return % only** (point-to-point from window open MV / price); Overview cards still use existing scalar Abs/XIRR/CAGR windows. Regenerate committed `openapi.json` + `api-types.ts`; extend handwritten `api.ts` with tests.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy, pytest, `uv`; Next.js web client via `openapi-typescript`, Vitest.

## Global Constraints

- Do **not** rename existing JSON field names (`ITD`, `1Y`, `3Y`, `5Y`, rates as fractions, excess as pp)
- Secrets never committed; never copy `.env` into docs or fixtures
- Services may keep returning plain `dict` — routers validate via `response_model`
- Do **not** hand-edit `apps/web/src/lib/api-types.ts` or `apps/web/openapi.json` — regenerate via `npm run generate:api` from repo root
- Every API task ends green: `cd apps/api && uv run pytest -q`
- After web client changes: `cd apps/web && npm test` and `npm run check:api` (from `apps/web` or root `npm run check:api`)
- Prefer edit over rewrite; YAGNI
- Out of scope for this plan: Next.js pages/components, chart library, Glossary copy, UI visual theme
- Follow-up plan (not this doc): `2026-08-02-portfolio-tracker-ui` web implementation

## Locked product decisions (API)

| Topic | Decision |
| ----- | -------- |
| Chart metric | Series API returns **absolute** cumulative return only (`metric: "absolute"`). XIRR/CAGR stay scalar on overview/holdings. UI chart Metric dropdown: Absolute uses series; XIRR/CAGR → empty/N/A until a later plan. |
| Window | Query param `window=ITD\|1Y\|3Y\|5Y`. If `metrics.window_start` is `None` (insufficient history) → `points: []`, `available: false`. |
| Portfolio series Y | `portfolio_return[t] = MV(t) / MV(base) - 1` where `base` is first day in `[start, as_of]` with `MV > 0` (usually window start). |
| Portfolio benchmark Y | Value-weighted at **base** day: `Σ w_i * (index_i(t)/index_i(base) - 1)` using mapped benchmarks; skip holdings with missing base index price (`incomplete: true` if any skipped with weight). |
| Holding series Y | `holding_return[t] = price(t)/price(base) - 1` (last close ≤ day); same for mapped index. |
| Sample dates | Sorted unique calendar dates from instrument `Price.price_date` (and for portfolio: union across held symbols) in `[start, as_of]`, always including `base` and `as_of` when a last-known price exists. Forward-fill last known close. |
| Caps | No downsampling in v1 (daily points OK). |
| Holding identity | `GET /portfolio/holdings/{instrument_id}` returns one `HoldingResponse` or 404. |
| Transactions | `GET /portfolio/holdings/{instrument_id}/transactions`; `amount = quantity * price` (fees exposed separately). |
| Catalogs | `GET /settings/catalogs` from `DEFAULT_BY_CATEGORY` keys + `INDEX_TICKERS` keys (order stable). |
| Last import report | **Not** persisted server-side (UI session/localStorage). |
| Stale holdings flag | **Not** added (UI uses `auth/status.last_sync_at` + `incomplete`). |

## File Structure

```
apps/api/src/portfolio_tracker/
  modules/
    portfolio/
      service.py          # Task 1–2: get_holding, list_transactions; mf_category on public row
      series.py           # Task 4–5: NEW — portfolio + holding absolute series
      types.py            # Task 2: HoldingPublic.mf_category
      __init__.py         # export new getters
    benchmarks.py         # Task 3: expose CATEGORY_CHOICES (or derive from DEFAULT_BY_CATEGORY)
  routers/
    portfolio.py          # Task 1, 4–5: new routes
    settings.py           # Task 3: catalogs route
  schemas/
    portfolio.py          # Task 1–2, 4–5: HoldingDetail schemas, Series schemas; mf_category
    settings.py           # Task 3: CatalogsResponse

apps/api/tests/
  test_portfolio_holding.py   # Task 1: NEW
  test_portfolio.py           # Task 2: mf_category assertions
  test_portfolio_series.py    # Task 4–5: NEW
  test_settings_catalogs.py   # Task 3: NEW
  test_openapi_portfolio.py   # Task 1, 4–5: path/schema presence
  test_openapi_auth_sync_settings.py  # Task 3: catalogs in OpenAPI

apps/web/
  openapi.json                # regenerate (never hand-edit)
  src/lib/api-types.ts        # regenerate
  src/lib/api.ts              # Task 6: new client methods
  src/__tests__/api.test.ts   # Task 6: request mapping tests
```

---

### Task 1: Holding detail + transactions endpoints

**Files:**
- Modify: `apps/api/src/portfolio_tracker/modules/portfolio/service.py`
- Modify: `apps/api/src/portfolio_tracker/modules/portfolio/__init__.py`
- Modify: `apps/api/src/portfolio_tracker/routers/portfolio.py`
- Modify: `apps/api/src/portfolio_tracker/schemas/portfolio.py`
- Create: `apps/api/tests/test_portfolio_holding.py`
- Modify: `apps/api/tests/test_openapi_portfolio.py`

**Interfaces:**
- Consumes: `get_holdings` / `_get_holdings_computed`, `Transaction` model, `load_portfolio_inputs`
- Produces:
  - `get_holding(session, instrument_id, as_of: str) -> dict | None` — same shape as one `HoldingPublic` row
  - `list_transactions(session, instrument_id: int) -> list[dict]` — ordered by `trade_date` asc, then `id` asc
  - `GET /portfolio/holdings/{instrument_id}` → `HoldingResponse` or 404
  - `GET /portfolio/holdings/{instrument_id}/transactions` → `HoldingTransactionsResponse` or 404 if instrument missing

- [ ] **Step 1: Write failing tests**

Create `apps/api/tests/test_portfolio_holding.py`:

```python
from fastapi.testclient import TestClient

from portfolio_tracker.db.engine import get_session_factory
from portfolio_tracker.db.models import (
    BenchmarkMap,
    BenchmarkPrice,
    Instrument,
    Price,
    Transaction,
)
from portfolio_tracker.main import create_app


def _seed_one(session):
    instrument = Instrument(
        symbol="RELIANCE",
        isin="INE002A01018",
        instrument_type="equity",
        exchange="NSE",
        yahoo_symbol="RELIANCE.NS",
    )
    session.add(instrument)
    session.flush()
    session.add_all(
        [
            Transaction(
                instrument_id=instrument.id,
                trade_date="2024-01-10",
                side="buy",
                quantity=5,
                price=2000.0,
                fees=10.0,
                source="csv",
                dedupe_key="h1",
            ),
            Transaction(
                instrument_id=instrument.id,
                trade_date="2024-02-01",
                side="buy",
                quantity=5,
                price=2100.0,
                fees=0.0,
                source="api",
                dedupe_key="h2",
            ),
            Price(
                symbol="RELIANCE.NS",
                price_date="2024-06-01",
                close=2600.0,
                source="yahoo",
            ),
            BenchmarkMap(
                instrument_id=instrument.id,
                benchmark_index="Nifty 500",
                source="default",
            ),
            BenchmarkPrice(
                index_symbol="Nifty 500",
                price_date="2024-06-01",
                close=12000.0,
            ),
        ]
    )
    session.commit()
    return instrument


def test_get_holding_and_transactions_http():
    client = TestClient(create_app())
    Session = get_session_factory()
    with Session() as session:
        instrument = _seed_one(session)
        instrument_id = instrument.id

    missing = client.get("/portfolio/holdings/99999")
    assert missing.status_code == 404

    holding = client.get(f"/portfolio/holdings/{instrument_id}")
    assert holding.status_code == 200
    body = holding.json()
    assert body["instrument_id"] == instrument_id
    assert body["symbol"] == "RELIANCE"
    assert body["qty"] == 10

    txs = client.get(f"/portfolio/holdings/{instrument_id}/transactions")
    assert txs.status_code == 200
    rows = txs.json()["transactions"]
    assert len(rows) == 2
    assert rows[0]["trade_date"] == "2024-01-10"
    assert rows[0]["side"] == "buy"
    assert rows[0]["quantity"] == 5
    assert rows[0]["price"] == 2000.0
    assert rows[0]["fees"] == 10.0
    assert rows[0]["amount"] == 10000.0
    assert rows[0]["source"] == "csv"
    assert rows[1]["source"] == "api"


def test_transactions_404_unknown_instrument():
    client = TestClient(create_app())
    assert client.get("/portfolio/holdings/99999/transactions").status_code == 404
```

Append to `apps/api/tests/test_openapi_portfolio.py`:

```python
def test_openapi_includes_holding_detail_paths():
    schema = TestClient(create_app()).get("/openapi.json").json()
    assert "/portfolio/holdings/{instrument_id}" in schema["paths"]
    assert "/portfolio/holdings/{instrument_id}/transactions" in schema["paths"]
    components = schema["components"]["schemas"]
    assert "HoldingTransactionsResponse" in components
    assert "TransactionRowResponse" in components
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/api && uv run pytest tests/test_portfolio_holding.py tests/test_openapi_portfolio.py::test_openapi_includes_holding_detail_paths -v`

Expected: FAIL (404/route missing or import/schema missing)

- [ ] **Step 3: Add schemas**

In `apps/api/src/portfolio_tracker/schemas/portfolio.py` add:

```python
class TransactionRowResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    trade_date: str
    side: str
    quantity: float
    price: float
    fees: float
    amount: float
    source: str


class HoldingTransactionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instrument_id: int
    transactions: list[TransactionRowResponse]
```

- [ ] **Step 4: Implement service helpers**

In `apps/api/src/portfolio_tracker/modules/portfolio/service.py` add:

```python
def get_holding(
    session: Session,
    instrument_id: int,
    as_of: str,
) -> dict | None:
    if session.get(Instrument, instrument_id) is None:
        return None
    for row in get_holdings(session, as_of):
        if row["instrument_id"] == instrument_id:
            return row
    # Instrument exists but filtered out (no qty/txs) — still 404 for UI drilldown
    return None


def list_transactions(session: Session, instrument_id: int) -> list[dict] | None:
    if session.get(Instrument, instrument_id) is None:
        return None
    rows = (
        session.query(Transaction)
        .filter(Transaction.instrument_id == instrument_id)
        .order_by(Transaction.trade_date.asc(), Transaction.id.asc())
        .all()
    )
    return [
        {
            "id": tx.id,
            "trade_date": tx.trade_date,
            "side": tx.side,
            "quantity": tx.quantity,
            "price": tx.price,
            "fees": tx.fees,
            "amount": tx.quantity * tx.price,
            "source": tx.source,
        }
        for tx in rows
    ]
```

Export from `modules/portfolio/__init__.py`:

```python
from portfolio_tracker.modules.portfolio.service import (
    get_holding,
    get_holdings,
    get_overview,
    get_performance,
    list_transactions,
)

__all__ = [
    "get_holding",
    "get_holdings",
    "get_overview",
    "get_performance",
    "list_transactions",
]
```

- [ ] **Step 5: Wire router**

In `apps/api/src/portfolio_tracker/routers/portfolio.py` add imports and routes **after** the collection `GET /holdings` route (FastAPI matches in order; static paths before parameterized is already fine if `/holdings` is registered first):

```python
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from portfolio_tracker.db.session import get_db
from portfolio_tracker.modules import portfolio, reconcile
from portfolio_tracker.schemas.portfolio import (
    AlertsResponse,
    HoldingResponse,
    HoldingsResponse,
    HoldingTransactionsResponse,
    OverviewResponse,
    PerformanceResponse,
)

# ... existing overview/holdings/alerts/performance ...


@router.get(
    "/holdings/{instrument_id}",
    response_model=HoldingResponse,
    responses={404: {"description": "Holding not found"}},
)
def holding_detail(
    instrument_id: int,
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    row = portfolio.get_holding(
        session, instrument_id, as_of=date.today().isoformat()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Holding not found")
    return row


@router.get(
    "/holdings/{instrument_id}/transactions",
    response_model=HoldingTransactionsResponse,
    responses={404: {"description": "Instrument not found"}},
)
def holding_transactions(
    instrument_id: int,
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    rows = portfolio.list_transactions(session, instrument_id)
    if rows is None:
        raise HTTPException(status_code=404, detail="Instrument not found")
    return {"instrument_id": instrument_id, "transactions": rows}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd apps/api && uv run pytest tests/test_portfolio_holding.py tests/test_openapi_portfolio.py -v`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add \
  apps/api/src/portfolio_tracker/modules/portfolio/service.py \
  apps/api/src/portfolio_tracker/modules/portfolio/__init__.py \
  apps/api/src/portfolio_tracker/routers/portfolio.py \
  apps/api/src/portfolio_tracker/schemas/portfolio.py \
  apps/api/tests/test_portfolio_holding.py \
  apps/api/tests/test_openapi_portfolio.py
git commit -m "$(cat <<'EOF'
feat(api): add holding detail and transactions endpoints

EOF
)"
```

---

### Task 2: Expose `mf_category` on holdings

**Files:**
- Modify: `apps/api/src/portfolio_tracker/modules/portfolio/types.py`
- Modify: `apps/api/src/portfolio_tracker/modules/portfolio/service.py` (public row assembly ~line 102–120)
- Modify: `apps/api/src/portfolio_tracker/schemas/portfolio.py` (`HoldingResponse`)
- Modify: `apps/api/tests/test_portfolio.py` (or `test_portfolio_holding.py`)

**Interfaces:**
- Consumes: `Instrument.mf_category`
- Produces: every holding JSON includes `mf_category: str | null`

- [ ] **Step 1: Write failing test**

Append to `apps/api/tests/test_portfolio_holding.py`:

```python
def test_holding_includes_mf_category():
    client = TestClient(create_app())
    Session = get_session_factory()
    with Session() as session:
        fund = Instrument(
            symbol="PARAGPARIKH",
            isin="INF879O01027",
            instrument_type="mf",
            mf_category="Flexi Cap",
            needs_category=0,
        )
        session.add(fund)
        session.flush()
        session.add_all(
            [
                Transaction(
                    instrument_id=fund.id,
                    trade_date="2024-01-10",
                    side="buy",
                    quantity=10,
                    price=100.0,
                    fees=0.0,
                    source="csv",
                    dedupe_key="mf1",
                ),
                Price(
                    symbol="INF879O01027",
                    price_date="2024-06-01",
                    close=120.0,
                    source="amfi",
                ),
                BenchmarkMap(
                    instrument_id=fund.id,
                    benchmark_index="Nifty 500",
                    source="default",
                ),
                BenchmarkPrice(
                    index_symbol="Nifty 500",
                    price_date="2024-06-01",
                    close=12000.0,
                ),
            ]
        )
        session.commit()
        fund_id = fund.id

    body = client.get(f"/portfolio/holdings/{fund_id}").json()
    assert body["mf_category"] == "Flexi Cap"
    assert body["instrument_type"] == "mf"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && uv run pytest tests/test_portfolio_holding.py::test_holding_includes_mf_category -v`

Expected: FAIL (missing field / validation)

- [ ] **Step 3: Minimal implementation**

`types.py` — add to `HoldingPublic`:

```python
mf_category: str | None
```

`service.py` — in `public_without_windows`:

```python
"mf_category": instrument.mf_category,
```

`schemas/portfolio.py` — on `HoldingResponse`:

```python
mf_category: str | None
```

- [ ] **Step 4: Run tests**

Run: `cd apps/api && uv run pytest tests/test_portfolio_holding.py tests/test_portfolio.py -v`

Expected: PASS (update any fixtures/assertions that construct full holding dicts if they break on extra required schema fields — response_model ignores unknown service keys but tests comparing exact keys may need the new field)

- [ ] **Step 5: Commit**

```bash
git add \
  apps/api/src/portfolio_tracker/modules/portfolio/types.py \
  apps/api/src/portfolio_tracker/modules/portfolio/service.py \
  apps/api/src/portfolio_tracker/schemas/portfolio.py \
  apps/api/tests/test_portfolio_holding.py
git commit -m "$(cat <<'EOF'
feat(api): include mf_category on holding responses

EOF
)"
```

---

### Task 3: Settings catalogs endpoint

**Files:**
- Modify: `apps/api/src/portfolio_tracker/modules/benchmarks.py`
- Modify: `apps/api/src/portfolio_tracker/schemas/settings.py`
- Modify: `apps/api/src/portfolio_tracker/routers/settings.py`
- Create: `apps/api/tests/test_settings_catalogs.py`
- Modify: `apps/api/tests/test_openapi_auth_sync_settings.py`

**Interfaces:**
- Consumes: `DEFAULT_BY_CATEGORY`, `INDEX_TICKERS`
- Produces: `GET /settings/catalogs` → `{ "mf_categories": [...], "benchmark_indexes": [...] }`

- [ ] **Step 1: Write failing tests**

Create `apps/api/tests/test_settings_catalogs.py`:

```python
from fastapi.testclient import TestClient

from portfolio_tracker.main import create_app
from portfolio_tracker.modules.benchmarks import DEFAULT_BY_CATEGORY
from portfolio_tracker.modules.index_tickers import INDEX_TICKERS


def test_settings_catalogs_match_backend_constants():
    client = TestClient(create_app())
    response = client.get("/settings/catalogs")
    assert response.status_code == 200
    body = response.json()
    assert body["mf_categories"] == list(DEFAULT_BY_CATEGORY.keys())
    assert body["benchmark_indexes"] == list(INDEX_TICKERS.keys())
```

Append to `apps/api/tests/test_openapi_auth_sync_settings.py` (or add assertion in the new file):

```python
def test_openapi_includes_settings_catalogs():
    from portfolio_tracker.main import create_app
    from fastapi.testclient import TestClient

    schema = TestClient(create_app()).get("/openapi.json").json()
    assert "/settings/catalogs" in schema["paths"]
    assert "CatalogsResponse" in schema["components"]["schemas"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/api && uv run pytest tests/test_settings_catalogs.py -v`

Expected: FAIL (404)

- [ ] **Step 3: Implement**

In `benchmarks.py` (optional clarity — router may import constants directly):

```python
MF_CATEGORY_CHOICES: list[str] = list(DEFAULT_BY_CATEGORY.keys())
```

In `schemas/settings.py`:

```python
class CatalogsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mf_categories: list[str]
    benchmark_indexes: list[str]
```

In `routers/settings.py`:

```python
from portfolio_tracker.modules.benchmarks import DEFAULT_BY_CATEGORY
from portfolio_tracker.modules.index_tickers import INDEX_TICKERS
from portfolio_tracker.schemas.settings import (
    BenchmarkBody,
    BenchmarkListResponse,
    BenchmarkUpdateResponse,
    CatalogsResponse,
    CategoryBody,
    CategoryUpdateResponse,
)


@router.get("/catalogs", response_model=CatalogsResponse)
def catalogs() -> dict:
    return {
        "mf_categories": list(DEFAULT_BY_CATEGORY.keys()),
        "benchmark_indexes": list(INDEX_TICKERS.keys()),
    }
```

- [ ] **Step 4: Run tests**

Run: `cd apps/api && uv run pytest tests/test_settings_catalogs.py tests/test_openapi_auth_sync_settings.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add \
  apps/api/src/portfolio_tracker/modules/benchmarks.py \
  apps/api/src/portfolio_tracker/schemas/settings.py \
  apps/api/src/portfolio_tracker/routers/settings.py \
  apps/api/tests/test_settings_catalogs.py \
  apps/api/tests/test_openapi_auth_sync_settings.py
git commit -m "$(cat <<'EOF'
feat(api): expose settings catalogs for category and index shortlists

EOF
)"
```

---

### Task 4: Portfolio absolute return series

**Files:**
- Create: `apps/api/src/portfolio_tracker/modules/portfolio/series.py`
- Modify: `apps/api/src/portfolio_tracker/modules/portfolio/__init__.py`
- Modify: `apps/api/src/portfolio_tracker/schemas/portfolio.py`
- Modify: `apps/api/src/portfolio_tracker/routers/portfolio.py`
- Create: `apps/api/tests/test_portfolio_series.py`
- Modify: `apps/api/tests/test_openapi_portfolio.py`

**Interfaces:**
- Consumes: `load_portfolio_inputs`, `_qty_at`, `_latest_price`, `_instrument_price_symbol`, `_benchmark_price`, `benchmarks.ensure_benchmark_map`, `metrics.window_start`
- Produces: `get_portfolio_series(session, as_of: str, window: str) -> dict`
- HTTP: `GET /portfolio/series?window=ITD` (default `ITD`) → `PortfolioSeriesResponse`

Response shape:

```json
{
  "window": "ITD",
  "metric": "absolute",
  "as_of": "2024-06-01",
  "start": "2022-01-03",
  "available": true,
  "incomplete": false,
  "points": [
    {"date": "2022-01-03", "portfolio_return": 0.0, "benchmark_return": 0.0},
    {"date": "2024-06-01", "portfolio_return": 0.3, "benchmark_return": 0.2}
  ]
}
```

- [ ] **Step 1: Write failing tests**

Create `apps/api/tests/test_portfolio_series.py`:

```python
from fastapi.testclient import TestClient

from portfolio_tracker.db.engine import get_session_factory
from portfolio_tracker.db.models import (
    BenchmarkMap,
    BenchmarkPrice,
    Instrument,
    Price,
    Transaction,
)
from portfolio_tracker.main import create_app
from portfolio_tracker.modules import portfolio


def _seed_series(session):
    instrument = Instrument(
        symbol="RELIANCE",
        isin="INE002A01018",
        instrument_type="equity",
        exchange="NSE",
        yahoo_symbol="RELIANCE.NS",
    )
    session.add(instrument)
    session.flush()
    session.add_all(
        [
            Transaction(
                instrument_id=instrument.id,
                trade_date="2022-01-03",
                side="buy",
                quantity=10,
                price=2000.0,
                fees=0,
                source="csv",
                dedupe_key="s1",
            ),
            Price(
                symbol="RELIANCE.NS",
                price_date="2022-01-03",
                close=2000.0,
                source="yahoo",
            ),
            Price(
                symbol="RELIANCE.NS",
                price_date="2023-06-02",
                close=2200.0,
                source="yahoo",
            ),
            Price(
                symbol="RELIANCE.NS",
                price_date="2024-06-01",
                close=2600.0,
                source="yahoo",
            ),
            BenchmarkMap(
                instrument_id=instrument.id,
                benchmark_index="Nifty 500",
                source="default",
            ),
            BenchmarkPrice(
                index_symbol="Nifty 500",
                price_date="2022-01-03",
                close=10000.0,
            ),
            BenchmarkPrice(
                index_symbol="Nifty 500",
                price_date="2023-06-02",
                close=11000.0,
            ),
            BenchmarkPrice(
                index_symbol="Nifty 500",
                price_date="2024-06-01",
                close=12000.0,
            ),
        ]
    )
    session.commit()
    return instrument


def test_portfolio_series_itd_absolute():
    Session = get_session_factory()
    with Session() as session:
        _seed_series(session)
        result = portfolio.get_portfolio_series(
            session, as_of="2024-06-01", window="ITD"
        )
    assert result["available"] is True
    assert result["metric"] == "absolute"
    assert result["start"] == "2022-01-03"
    by_date = {p["date"]: p for p in result["points"]}
    assert by_date["2022-01-03"]["portfolio_return"] == 0.0
    assert abs(by_date["2024-06-01"]["portfolio_return"] - 0.3) < 1e-9
    assert abs(by_date["2024-06-01"]["benchmark_return"] - 0.2) < 1e-9


def test_portfolio_series_http_and_unavailable_window():
    client = TestClient(create_app())
    Session = get_session_factory()
    with Session() as session:
        _seed_series(session)

    ok = client.get("/portfolio/series", params={"window": "ITD"})
    assert ok.status_code == 200
    assert ok.json()["metric"] == "absolute"
    assert len(ok.json()["points"]) >= 2

    # Holding starts 2022; as_of today may make 5Y available — force via service:
    Session = get_session_factory()
    with Session() as session:
        # inception 2022-01-03; window 5Y from 2022-06-01 starts 2017 → N/A
        result = portfolio.get_portfolio_series(
            session, as_of="2022-06-01", window="5Y"
        )
    assert result["available"] is False
    assert result["points"] == []


def test_portfolio_series_rejects_bad_window():
    client = TestClient(create_app())
    response = client.get("/portfolio/series", params={"window": "YTD"})
    assert response.status_code == 400
```

Append OpenAPI check:

```python
def test_openapi_includes_portfolio_series():
    schema = TestClient(create_app()).get("/openapi.json").json()
    assert "/portfolio/series" in schema["paths"]
    assert "PortfolioSeriesResponse" in schema["components"]["schemas"]
    assert "SeriesPoint" in schema["components"]["schemas"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/api && uv run pytest tests/test_portfolio_series.py tests/test_openapi_portfolio.py::test_openapi_includes_portfolio_series -v`

Expected: FAIL

- [ ] **Step 3: Add schemas**

```python
class SeriesPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: str
    portfolio_return: float | None = None
    benchmark_return: float | None = None
    holding_return: float | None = None


class PortfolioSeriesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    window: WindowKey
    metric: Literal["absolute"]
    as_of: str
    start: str | None
    available: bool
    incomplete: bool
    points: list[SeriesPoint]
```

Add `Literal` import from `typing` in `schemas/portfolio.py` (or use `typing.Literal`). Import `WindowKey` from common if not already.

- [ ] **Step 4: Implement `series.py`**

Create `apps/api/src/portfolio_tracker/modules/portfolio/series.py`:

```python
from __future__ import annotations

from sqlalchemy.orm import Session

from portfolio_tracker.db.models import Instrument, Price, Transaction
from portfolio_tracker.modules import benchmarks, metrics
from portfolio_tracker.modules.portfolio.data import (
    _benchmark_price,
    _instrument_price_symbol,
    _latest_price,
    load_portfolio_inputs,
)
from portfolio_tracker.modules.portfolio.windows import _qty_at

VALID_WINDOWS = ("ITD", "1Y", "3Y", "5Y")


def _empty_series(window: str, as_of: str, *, start: str | None = None) -> dict:
    return {
        "window": window,
        "metric": "absolute",
        "as_of": as_of,
        "start": start,
        "available": False,
        "incomplete": False,
        "points": [],
    }


def _price_dates(session: Session, symbols: set[str], start: str, as_of: str) -> list[str]:
    if not symbols:
        return []
    rows = (
        session.query(Price.price_date)
        .filter(
            Price.symbol.in_(symbols),
            Price.price_date >= start,
            Price.price_date <= as_of,
        )
        .distinct()
        .order_by(Price.price_date.asc())
        .all()
    )
    return [row[0] for row in rows]


def _portfolio_mv_on_day(
    session: Session,
    instruments: list[Instrument],
    transactions_by_instrument: dict[int, list[Transaction]],
    day: str,
) -> tuple[float, dict[int, float], bool]:
    """Return (total_mv, value_by_instrument_id, incomplete)."""
    total = 0.0
    values: dict[int, float] = {}
    incomplete = False
    for instrument in instruments:
        txs = transactions_by_instrument.get(instrument.id, [])
        qty = _qty_at(txs, day)
        if qty <= 0:
            continue
        price = _latest_price(session, _instrument_price_symbol(instrument), day)
        if price is None:
            incomplete = True
            continue
        value = qty * price
        values[instrument.id] = value
        total += value
    return total, values, incomplete


def get_portfolio_series(session: Session, as_of: str, window: str) -> dict:
    if window not in VALID_WINDOWS:
        raise ValueError(f"Unknown window: {window}")

    inputs = load_portfolio_inputs(session, as_of)
    all_txs = sorted(
        (
            tx
            for txs in inputs.transactions_by_instrument.values()
            for tx in txs
        ),
        key=lambda tx: tx.trade_date,
    )
    if not all_txs:
        return _empty_series(window, as_of)

    inception = all_txs[0].trade_date
    start = metrics.window_start(as_of, window, inception)
    if start is None:
        return _empty_series(window, as_of)

    # Find base day: first day with MV > 0 on/after start
    symbols = {
        _instrument_price_symbol(inst)
        for inst in inputs.instruments
        if inputs.transactions_by_instrument.get(inst.id)
    }
    candidate_dates = _price_dates(session, symbols, start, as_of)
    if as_of not in candidate_dates:
        candidate_dates = [*candidate_dates, as_of]

    base_day: str | None = None
    base_mv = 0.0
    base_values: dict[int, float] = {}
    incomplete = False
    for day in candidate_dates:
        mv, values, day_incomplete = _portfolio_mv_on_day(
            session,
            inputs.instruments,
            inputs.transactions_by_instrument,
            day,
        )
        incomplete = incomplete or day_incomplete
        if mv > 0:
            base_day = day
            base_mv = mv
            base_values = values
            break
    if base_day is None or base_mv <= 0:
        return _empty_series(window, as_of, start=start)

    # Base index levels per instrument with weight
    base_index: dict[int, tuple[str, float, float]] = {}
    for instrument_id, value in base_values.items():
        instrument = session.get(Instrument, instrument_id)
        if instrument is None:
            continue
        weight = value / base_mv
        bmap = benchmarks.ensure_benchmark_map(session, instrument)
        level = _benchmark_price(
            session, bmap.benchmark_index, base_day, as_of=as_of
        )
        if level is None or level <= 0:
            incomplete = True
            continue
        base_index[instrument_id] = (bmap.benchmark_index, level, weight)

    points: list[dict] = []
    for day in [d for d in candidate_dates if d >= base_day]:
        mv, _values, day_incomplete = _portfolio_mv_on_day(
            session,
            inputs.instruments,
            inputs.transactions_by_instrument,
            day,
        )
        incomplete = incomplete or day_incomplete
        portfolio_return = (mv / base_mv - 1.0) if mv > 0 else None
        bench = 0.0
        bench_ok = True
        if not base_index:
            bench_ok = False
        for index_name, base_level, weight in base_index.values():
            level = _benchmark_price(session, index_name, day, as_of=as_of)
            if level is None or base_level <= 0:
                bench_ok = False
                break
            bench += weight * (level / base_level - 1.0)
        points.append(
            {
                "date": day,
                "portfolio_return": portfolio_return,
                "benchmark_return": bench if bench_ok else None,
                "holding_return": None,
            }
        )

    return {
        "window": window,
        "metric": "absolute",
        "as_of": as_of,
        "start": start,
        "available": True,
        "incomplete": incomplete,
        "points": points,
    }
```

Export `get_portfolio_series` from `modules/portfolio/__init__.py`.

- [ ] **Step 5: Wire router**

```python
from portfolio_tracker.schemas.portfolio import (
    # ...existing...
    PortfolioSeriesResponse,
)
from portfolio_tracker.schemas.common import WindowKey


@router.get(
    "/series",
    response_model=PortfolioSeriesResponse,
    responses={400: {"description": "Invalid window"}},
)
def portfolio_series(
    session: Annotated[Session, Depends(get_db)],
    window: WindowKey = "ITD",
) -> dict:
    try:
        return portfolio.get_portfolio_series(
            session, as_of=date.today().isoformat(), window=window
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
```

Note: register `/series` **before** any conflicting paths; it is under prefix `/portfolio`, so path is `/portfolio/series`. Keep it near other collection routes (overview/holdings), not under `{instrument_id}`.

- [ ] **Step 6: Run tests**

Run: `cd apps/api && uv run pytest tests/test_portfolio_series.py tests/test_openapi_portfolio.py -v`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add \
  apps/api/src/portfolio_tracker/modules/portfolio/series.py \
  apps/api/src/portfolio_tracker/modules/portfolio/__init__.py \
  apps/api/src/portfolio_tracker/schemas/portfolio.py \
  apps/api/src/portfolio_tracker/routers/portfolio.py \
  apps/api/tests/test_portfolio_series.py \
  apps/api/tests/test_openapi_portfolio.py
git commit -m "$(cat <<'EOF'
feat(api): add portfolio absolute return series for charts

EOF
)"
```

---

### Task 5: Holding absolute return series

**Files:**
- Modify: `apps/api/src/portfolio_tracker/modules/portfolio/series.py`
- Modify: `apps/api/src/portfolio_tracker/modules/portfolio/__init__.py`
- Modify: `apps/api/src/portfolio_tracker/schemas/portfolio.py`
- Modify: `apps/api/src/portfolio_tracker/routers/portfolio.py`
- Modify: `apps/api/tests/test_portfolio_series.py`
- Modify: `apps/api/tests/test_openapi_portfolio.py`

**Interfaces:**
- Consumes: same price helpers + `ensure_benchmark_map`
- Produces: `get_holding_series(session, instrument_id, as_of, window) -> dict | None` (`None` = unknown instrument)
- HTTP: `GET /portfolio/holdings/{instrument_id}/series?window=ITD` → `HoldingSeriesResponse` or 404

Response shape:

```json
{
  "instrument_id": 1,
  "window": "ITD",
  "metric": "absolute",
  "benchmark": "Nifty 500",
  "as_of": "2024-06-01",
  "start": "2022-01-03",
  "available": true,
  "incomplete": false,
  "points": [
    {"date": "2022-01-03", "holding_return": 0.0, "benchmark_return": 0.0},
    {"date": "2024-06-01", "holding_return": 0.3, "benchmark_return": 0.2}
  ]
}
```

- [ ] **Step 1: Write failing tests**

Append to `apps/api/tests/test_portfolio_series.py`:

```python
def test_holding_series_itd_absolute():
    Session = get_session_factory()
    with Session() as session:
        instrument = _seed_series(session)
        result = portfolio.get_holding_series(
            session,
            instrument.id,
            as_of="2024-06-01",
            window="ITD",
        )
    assert result is not None
    assert result["available"] is True
    assert result["benchmark"] == "Nifty 500"
    by_date = {p["date"]: p for p in result["points"]}
    assert by_date["2022-01-03"]["holding_return"] == 0.0
    assert abs(by_date["2024-06-01"]["holding_return"] - 0.3) < 1e-9
    assert abs(by_date["2024-06-01"]["benchmark_return"] - 0.2) < 1e-9


def test_holding_series_http():
    client = TestClient(create_app())
    Session = get_session_factory()
    with Session() as session:
        instrument = _seed_series(session)
        instrument_id = instrument.id

    response = client.get(
        f"/portfolio/holdings/{instrument_id}/series",
        params={"window": "ITD"},
    )
    assert response.status_code == 200
    assert response.json()["instrument_id"] == instrument_id
    assert client.get("/portfolio/holdings/99999/series").status_code == 404
```

OpenAPI:

```python
def test_openapi_includes_holding_series():
    schema = TestClient(create_app()).get("/openapi.json").json()
    assert "/portfolio/holdings/{instrument_id}/series" in schema["paths"]
    assert "HoldingSeriesResponse" in schema["components"]["schemas"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/api && uv run pytest tests/test_portfolio_series.py::test_holding_series_itd_absolute tests/test_portfolio_series.py::test_holding_series_http -v`

Expected: FAIL

- [ ] **Step 3: Schema + implementation**

```python
class HoldingSeriesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instrument_id: int
    window: WindowKey
    metric: Literal["absolute"]
    benchmark: str
    as_of: str
    start: str | None
    available: bool
    incomplete: bool
    points: list[SeriesPoint]
```

In `series.py` add:

```python
def get_holding_series(
    session: Session,
    instrument_id: int,
    as_of: str,
    window: str,
) -> dict | None:
    if window not in VALID_WINDOWS:
        raise ValueError(f"Unknown window: {window}")
    instrument = session.get(Instrument, instrument_id)
    if instrument is None:
        return None

    txs = (
        session.query(Transaction)
        .filter(
            Transaction.instrument_id == instrument_id,
            Transaction.trade_date <= as_of,
        )
        .order_by(Transaction.trade_date.asc())
        .all()
    )
    if not txs:
        return {
            "instrument_id": instrument_id,
            "window": window,
            "metric": "absolute",
            "benchmark": benchmarks.ensure_benchmark_map(
                session, instrument
            ).benchmark_index,
            "as_of": as_of,
            "start": None,
            "available": False,
            "incomplete": False,
            "points": [],
        }

    inception = txs[0].trade_date
    start = metrics.window_start(as_of, window, inception)
    bmap = benchmarks.ensure_benchmark_map(session, instrument)
    if start is None:
        return {
            "instrument_id": instrument_id,
            "window": window,
            "metric": "absolute",
            "benchmark": bmap.benchmark_index,
            "as_of": as_of,
            "start": None,
            "available": False,
            "incomplete": False,
            "points": [],
        }

    symbol = _instrument_price_symbol(instrument)
    dates = _price_dates(session, {symbol}, start, as_of)
    if as_of not in dates:
        dates = [*dates, as_of]

    base_day = None
    base_price = None
    for day in dates:
        price = _latest_price(session, symbol, day)
        if price is not None and price > 0:
            base_day = day
            base_price = price
            break
    if base_day is None or base_price is None:
        return {
            "instrument_id": instrument_id,
            "window": window,
            "metric": "absolute",
            "benchmark": bmap.benchmark_index,
            "as_of": as_of,
            "start": start,
            "available": False,
            "incomplete": True,
            "points": [],
        }

    base_bench = _benchmark_price(
        session, bmap.benchmark_index, base_day, as_of=as_of
    )
    incomplete = base_bench is None or base_bench <= 0
    points: list[dict] = []
    for day in [d for d in dates if d >= base_day]:
        price = _latest_price(session, symbol, day)
        holding_return = (
            (price / base_price - 1.0) if price is not None else None
        )
        bench_level = _benchmark_price(
            session, bmap.benchmark_index, day, as_of=as_of
        )
        benchmark_return = (
            (bench_level / base_bench - 1.0)
            if bench_level is not None and base_bench and base_bench > 0
            else None
        )
        if holding_return is None or benchmark_return is None:
            incomplete = True
        points.append(
            {
                "date": day,
                "holding_return": holding_return,
                "benchmark_return": benchmark_return,
                "portfolio_return": None,
            }
        )

    return {
        "instrument_id": instrument_id,
        "window": window,
        "metric": "absolute",
        "benchmark": bmap.benchmark_index,
        "as_of": as_of,
        "start": start,
        "available": True,
        "incomplete": incomplete,
        "points": points,
    }
```

Router:

```python
from portfolio_tracker.schemas.portfolio import HoldingSeriesResponse


@router.get(
    "/holdings/{instrument_id}/series",
    response_model=HoldingSeriesResponse,
    responses={
        400: {"description": "Invalid window"},
        404: {"description": "Instrument not found"},
    },
)
def holding_series(
    instrument_id: int,
    session: Annotated[Session, Depends(get_db)],
    window: WindowKey = "ITD",
) -> dict:
    try:
        result = portfolio.get_holding_series(
            session,
            instrument_id,
            as_of=date.today().isoformat(),
            window=window,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Instrument not found")
    return result
```

Export `get_holding_series` from `__init__.py`.

- [ ] **Step 4: Run tests**

Run: `cd apps/api && uv run pytest tests/test_portfolio_series.py tests/test_openapi_portfolio.py -v`

Expected: PASS

- [ ] **Step 5: Full API suite**

Run: `cd apps/api && uv run pytest -q`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add \
  apps/api/src/portfolio_tracker/modules/portfolio/series.py \
  apps/api/src/portfolio_tracker/modules/portfolio/__init__.py \
  apps/api/src/portfolio_tracker/schemas/portfolio.py \
  apps/api/src/portfolio_tracker/routers/portfolio.py \
  apps/api/tests/test_portfolio_series.py \
  apps/api/tests/test_openapi_portfolio.py
git commit -m "$(cat <<'EOF'
feat(api): add holding absolute return series for detail charts

EOF
)"
```

---

### Task 6: Regenerate OpenAPI + extend web `api.ts`

**Files:**
- Regenerate: `apps/web/openapi.json`, `apps/web/src/lib/api-types.ts`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/__tests__/api.test.ts`

**Interfaces:**
- Consumes: new OpenAPI paths from Tasks 1–5
- Produces: typed client methods used by the future UI plan

- [ ] **Step 1: Regenerate artifacts**

Run from repo root:

```bash
npm run generate:api
npm run check:api
```

Expected: exit 0; `openapi.json` / `api-types.ts` updated with new paths

- [ ] **Step 2: Write failing client tests**

Append to `apps/web/src/__tests__/api.test.ts`:

```typescript
it("getHolding GETs /portfolio/holdings/:id", async () => {
  const fetchMock = mockOk({ instrument_id: 7, symbol: "RELIANCE" });
  await api.getHolding(7);
  expectGetRequest(fetchMock, "/portfolio/holdings/7");
});

it("getHoldingTransactions GETs transactions path", async () => {
  const fetchMock = mockOk({ instrument_id: 7, transactions: [] });
  await api.getHoldingTransactions(7);
  expectGetRequest(fetchMock, "/portfolio/holdings/7/transactions");
});

it("getPortfolioSeries GETs /portfolio/series with window", async () => {
  const fetchMock = mockOk({
    window: "1Y",
    metric: "absolute",
    as_of: "2026-08-01",
    start: "2025-08-01",
    available: true,
    incomplete: false,
    points: [],
  });
  await api.getPortfolioSeries("1Y");
  expect(fetchMock).toHaveBeenCalledWith(
    `${BASE}/portfolio/series?window=1Y`,
    expect.objectContaining({ cache: "no-store" }),
  );
});

it("getHoldingSeries GETs holding series with window", async () => {
  const fetchMock = mockOk({
    instrument_id: 7,
    window: "ITD",
    metric: "absolute",
    benchmark: "Nifty 500",
    as_of: "2026-08-01",
    start: "2024-01-01",
    available: true,
    incomplete: false,
    points: [],
  });
  await api.getHoldingSeries(7, "ITD");
  expect(fetchMock).toHaveBeenCalledWith(
    `${BASE}/portfolio/holdings/7/series?window=ITD`,
    expect.objectContaining({ cache: "no-store" }),
  );
});

it("getCatalogs GETs /settings/catalogs", async () => {
  const fetchMock = mockOk({ mf_categories: [], benchmark_indexes: [] });
  await api.getCatalogs();
  expectGetRequest(fetchMock, "/settings/catalogs");
});
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd apps/web && npm test`

Expected: FAIL (methods missing)

- [ ] **Step 4: Extend `api.ts`**

```typescript
export type HoldingTransactions = AppJson<
  "/portfolio/holdings/{instrument_id}/transactions",
  "get"
>;
export type PortfolioSeries = AppJson<"/portfolio/series", "get">;
export type HoldingSeries = AppJson<
  "/portfolio/holdings/{instrument_id}/series",
  "get"
>;
export type Catalogs = AppJson<"/settings/catalogs", "get">;

// inside api object:
  getHolding: (instrumentId: number) =>
    request<AppJson<"/portfolio/holdings/{instrument_id}", "get">>(
      `/portfolio/holdings/${instrumentId}`,
    ),
  getHoldingTransactions: (instrumentId: number) =>
    request<HoldingTransactions>(
      `/portfolio/holdings/${instrumentId}/transactions`,
    ),
  getPortfolioSeries: (window: "ITD" | "1Y" | "3Y" | "5Y" = "ITD") =>
    request<PortfolioSeries>(
      `/portfolio/series?window=${encodeURIComponent(window)}`,
    ),
  getHoldingSeries: (
    instrumentId: number,
    window: "ITD" | "1Y" | "3Y" | "5Y" = "ITD",
  ) =>
    request<HoldingSeries>(
      `/portfolio/holdings/${instrumentId}/series?window=${encodeURIComponent(window)}`,
    ),
  getCatalogs: () => request<Catalogs>("/settings/catalogs"),
```

If `AppJson` resolution fails for path-templated keys, use the generated operation response types from `api-types` the same way existing methods do — mirror whatever pattern `putBenchmark` already uses for `{instrument_id}` paths.

- [ ] **Step 5: Run web + monorepo checks**

```bash
cd apps/web && npm test
cd ../.. && npm run check:api && npm test
```

Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add \
  apps/web/openapi.json \
  apps/web/src/lib/api-types.ts \
  apps/web/src/lib/api.ts \
  apps/web/src/__tests__/api.test.ts
git commit -m "$(cat <<'EOF'
feat(web): regenerate OpenAPI client for UI API gaps

EOF
)"
```

---

## Self-review

**1. Spec coverage (UI design → this backend plan)**

| UI need | Task |
| ------- | ---- |
| Overview value/returns/windows | Already existed |
| Overview line chart | Task 4 |
| Holdings tables + category column | Existing + Task 2 |
| Holding detail identity | Task 1 |
| Holding chart | Task 5 |
| Transactions table | Task 1 |
| Import CSV + gap | Already existed |
| Settings auth/sync/benchmarks | Already existed |
| Data-driven category/index lists | Task 3 |
| Glossary | No API |
| Client typed access | Task 6 |

**2. Placeholder scan:** No TBD/TODO steps; series algorithm and response shapes specified.

**3. Type consistency:** `WindowKey`, `metric: "absolute"`, `SeriesPoint` field names shared; client methods use same path templates as routers.

**Deferred to UI plan:** dark shell, pages, Recharts, Metric N/A on charts for XIRR/CAGR, session storage for last import report, stale banner heuristics.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-02-ui-api-gaps.md`. Two execution options:

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?

After this plan lands, next doc: UI implementation plan against `2026-08-02-portfolio-tracker-ui-design.md` wiring these endpoints.
