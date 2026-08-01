# Portfolio Tracker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a local self-hosted Zerodha equity + Console MF portfolio tracker (Next.js + FastAPI + SQLite) with Console tradebook CSV import, Kite sync, Yahoo/AMFI prices, and Absolute/CAGR/XIRR plus multi-type benchmark excess for inception-to-date and trailing 1Y/3Y/5Y windows when history allows.

**Architecture:** Monorepo with `apps/api` (FastAPI modules: auth, sync, import, prices, benchmarks, metrics, portfolio, reconcile) writing to a gitignored SQLite file under `data/`, and `apps/web` (Next.js App Router) calling the API. PriceProvider abstracts Yahoo Finance + AMFI so paid Kite market data can swap in later. One clone = one local user = one DB.

**Tech Stack:** Python 3.12+ via `uv`, FastAPI, SQLAlchemy 2.0, SQLite, pytest, httpx; Next.js 15 (App Router) + TypeScript + npm; Vitest + Testing Library; `kiteconnect`, `yfinance`, AMFI/mfapi.in for NAVs; `numpy-financial` for XIRR.

## Global Constraints

- Returns windows (v1): **ITD** (inception-to-date) plus trailing **1Y / 3Y / 5Y** when history allows. No free custom date picker / YTD-only control in v1
- Rolling window rule: window ends at `as_of`; start = `as_of − N` calendar years (1→365d, 3→1095d, 5→1825d). If first cashflow/trade in scope is after window start → that window is **N/A**
- Per window, when possible: Absolute, XIRR, CAGR, and excess (absolute + XIRR + CAGR). CAGR still requires span ≥ 365 days (so 1Y/3Y/5Y qualify when the window is fully available; ITD CAGR only if ITD span ≥ 365d)
- Dividends excluded from XIRR / absolute return; no corporate-action engine
- Do not suppress CAGR solely because of multiple buys/SIPs
- Excess / outperformance: vs value-weighted (portfolio) or mapped (instrument) benchmark **over the same window** for absolute %, XIRR, and CAGR whenever both sides exist
- **Excess units (locked):** `absolute_excess_pp` = (port absolute % − bench point-to-point %) × 100; `cagr_excess_pp` = (port CAGR − bench CAGR) × 100; `xirr_excess_pp` = (port XIRR − **benchmark XIRR**) × 100. Benchmark XIRR uses the **same ₹ cashflows/dates** invested into the mapped index (buy index units on buys, reduce on sells, terminal = remaining index MV). Never compare XIRR to a raw point-to-point bench return
- Rolling absolute (UI copy): point-to-point opening MV → terminal MV when opening MV > 0 — **price/path return, not cashflow-adjusted**; label accordingly so SIP users are not misled
- CSV: Console **equity** tradebook + Console **Mutual Funds** tradebook only (one Console export family); header/segment-based detection; all-or-nothing parse; multi-file OK (Console ≤365 days per download). **Validate fixture headers against a real Console export before Task 4** (or replace fixtures when first real file is available)
- Prefer split of large tasks: Task 8 is **8a / 8b / 8c** (do not merge); keep Tasks 12+13 separate
- Non-delivery / unexpected segments: do **not** hard-filter yet — import parseable rows, return `segment_counts` + `flagged_rows` in import result so we can decide filtering after seeing real data
- Transactions only from CSV import or Kite API append — no manual txn entry UI
- MF category: auto from AMFI when possible; Settings override; unknown → Nifty 500 + set-category flag
- Yahoo equity symbols: try `{SYMBOL}.NS` then `{SYMBOL}.BO` on miss (most reliable for NSE/BSE)
- Index tickers: Nifty 500 `^CRSLDX`, Nifty 100 `^CNX100`, Nifty Midcap 150 `NIFTYMIDCAP150.NS`, Nifty Smallcap 250 `NIFTYSMLCAP250.NS`, Nifty 50 `^NSEI`
- Token validity: presence + Kite auth errors → reconnect banner; no 6 AM IST clock logic in v1
- Metrics cache table: **v2** — recompute on read in v1
- Kite Connect Personal only (no market data from Kite in v1)
- No real Zerodha credentials in CI; secrets never committed; no secrets in logs/API responses
- SQLite path: `data/portfolio.db` (gitignored); config via `.env` from `.env.example`
- Repo layout: `apps/web/`, `apps/api/`, `data/`, `docs/superpowers/`, `.env.example`, `README.md`
- Keep small verifiable tasks (do not merge Task 1+2, 8a+8b+8c, or 12+13)

## Locked decisions (post-review)

| # | Decision |
|---|----------|
| 1 | MF history = Console → Reports → Tradebook → Mutual Funds (same column family as equity). Not Coin Order History. |
| 2 | Segment filtering deferred; observe via import `segment_counts` / `flagged_rows`. |
| 3 | Absolute + XIRR + CAGR whenever possible for **ITD + trailing 1Y/3Y/5Y** (N/A if insufficient history). No custom date picker in v1. |
| 4 | Excess shown for absolute and XIRR (and CAGR when possible) **per window**, not a single return type only. |
| 4a | XIRR excess = port XIRR − same-cashflow **benchmark XIRR** (index units). Absolute excess vs point-to-point bench %. CAGR excess vs bench CAGR. |
| 4b | Portfolio `cagr_excess_pp` = port CAGR − value-weighted blend of per-instrument bench CAGRs (not `None` when computable). |
| 5 | Qty/avg from Kite holdings when present; cashflows from CSV/API txs only; reconcile → prompt CSV backfill / re-sync (no manual edits). |
| 6 | Yahoo: `.NS` then `.BO`. |
| 7 | No `metrics_cache` in v1 (design spec aligned; recompute on read). |
| 8 | Token: reconnect on missing token or Kite auth failure. |
| 9 | Gaps: Import + Overview communicate missing date range so user exports that slice specifically. Calendar days in v1 (not trading-day calendar). |
| 10 | Keep bite-sized tasks — Task 8 split into 8a/8b/8c. |
| 11 | `GET /portfolio/holdings` includes per-row `windows` (same shape as overview). |
| 12 | Settings helpers are public: `get_setting` / `set_setting` (no `_`-private use from other modules). |

---

## File Structure

```
portfolio-tracker/
  .env.example
  .gitignore
  README.md
  package.json                 # root scripts: api / web / test
  apps/
    api/
      pyproject.toml
      README.md
      src/portfolio_tracker/
        __init__.py
        main.py                # FastAPI app factory + routers
        config.py              # Settings from env
        db/
          __init__.py
          engine.py            # SQLite engine + session
          models.py            # SQLAlchemy tables
          session.py
        modules/
          kite_auth.py
          kite_sync.py
          csv_import.py
          portfolio.py
          metrics.py
          benchmarks.py
          prices/
            __init__.py
            base.py            # PriceProvider protocol
            yahoo.py
            amfi.py
            service.py         # orchestrates providers + cache
          reconcile.py
        routers/
          auth.py
          sync.py
          import_.py
          portfolio.py
          settings.py
          health.py
        schemas/
          __init__.py
          common.py
      tests/
        conftest.py
        fixtures/
          equity_tradebook.csv
          mf_tradebook.csv
          amfi_sample.json
        test_health.py
        test_db_models.py
        test_kite_auth.py
        test_csv_import.py
        test_prices.py
        test_benchmarks.py
        test_metrics.py
        test_portfolio.py
        test_kite_sync.py
        test_reconcile.py
        test_api_integration.py
    web/
      package.json
      tsconfig.json
      next.config.ts
      vitest.config.ts
      src/
        app/
          layout.tsx
          page.tsx             # Overview
          holdings/page.tsx
          performance/page.tsx
          import/page.tsx
          settings/page.tsx
          globals.css
        components/
          MetricCard.tsx
          HoldingsTable.tsx
          Banner.tsx
          AllocationChart.tsx
          PerformanceChart.tsx
          EmptyState.tsx
          Nav.tsx
        lib/
          api.ts               # typed fetch client
          types.ts
          format.ts
        __tests__/
          MetricCard.test.tsx
          HoldingsTable.test.tsx
          Banner.test.tsx
          EmptyState.test.tsx
  data/                        # gitignored; created at runtime
```

---

### Task 1: Monorepo scaffold + API health

**Files:**
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/src/portfolio_tracker/__init__.py`
- Create: `apps/api/src/portfolio_tracker/main.py`
- Create: `apps/api/src/portfolio_tracker/config.py`
- Create: `apps/api/src/portfolio_tracker/routers/health.py`
- Create: `apps/api/tests/conftest.py`
- Create: `apps/api/tests/test_health.py`
- Create: `.env.example`
- Create: `package.json` (root)
- Modify: `.gitignore`

**Interfaces:**
- Consumes: nothing
- Produces: FastAPI app via `create_app()`; `GET /health` → `{"status": "ok"}`; `Settings` dataclass from env (`kite_api_key`, `kite_api_secret`, `kite_redirect_url`, `database_url`, `cors_origins`)

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_health.py
from fastapi.testclient import TestClient
from portfolio_tracker.main import create_app


def test_health_returns_ok():
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && uv run pytest tests/test_health.py -v`

Expected: FAIL with `ModuleNotFoundError` or collection error (package not installed / `create_app` missing)

- [ ] **Step 3: Write minimal implementation**

```toml
# apps/api/pyproject.toml
[project]
name = "portfolio-tracker-api"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115.0",
  "uvicorn[standard]>=0.32.0",
  "sqlalchemy>=2.0.36",
  "pydantic-settings>=2.6.0",
  "httpx>=0.28.0",
  "python-multipart>=0.0.17",
  "kiteconnect>=5.0.1",
  "yfinance>=0.2.50",
  "numpy>=2.1.0",
  "numpy-financial>=1.0.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.3.0", "pytest-asyncio>=0.24.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/portfolio_tracker"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

```python
# apps/api/src/portfolio_tracker/__init__.py
"""Local Zerodha portfolio tracker API."""

__version__ = "0.1.0"
```

```python
# apps/api/src/portfolio_tracker/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    kite_api_key: str = ""
    kite_api_secret: str = ""
    kite_redirect_url: str = "http://127.0.0.1:8000/auth/callback"
    database_url: str = "sqlite:///../../data/portfolio.db"
    cors_origins: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

```python
# apps/api/src/portfolio_tracker/routers/health.py
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

```python
# apps/api/src/portfolio_tracker/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from portfolio_tracker.config import get_settings
from portfolio_tracker.routers import health


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Portfolio Tracker API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    return app


app = create_app()
```

```python
# apps/api/tests/conftest.py
import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _test_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("KITE_API_KEY", "test_key")
    monkeypatch.setenv("KITE_API_SECRET", "test_secret")
    monkeypatch.setenv("KITE_REDIRECT_URL", "http://127.0.0.1:8000/auth/callback")
    from portfolio_tracker.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
```

```env
# .env.example
KITE_API_KEY=
KITE_API_SECRET=
KITE_REDIRECT_URL=http://127.0.0.1:8000/auth/callback
DATABASE_URL=sqlite:///./data/portfolio.db
CORS_ORIGINS=http://localhost:3000
```

```json
{
  "name": "portfolio-tracker",
  "private": true,
  "scripts": {
    "api": "cd apps/api && uv run uvicorn portfolio_tracker.main:app --reload --port 8000",
    "api:test": "cd apps/api && uv run pytest -v",
    "web": "npm --prefix apps/web run dev",
    "web:test": "npm --prefix apps/web test",
    "test": "npm run api:test && npm run web:test"
  }
}
```

Append to `.gitignore` if missing:

```
data/
.env
.DS_Store
**/__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
node_modules/
.next/
.venv/
*.db
apps/api/.venv/
dist/
*.egg-info/
```

Also create empty `apps/api/src/portfolio_tracker/routers/__init__.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/api && uv sync --extra dev && uv run pytest tests/test_health.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .env.example .gitignore package.json apps/api
git commit -m "chore: scaffold FastAPI app with health endpoint"
```

---

### Task 2: SQLite schema + session helpers

**Files:**
- Create: `apps/api/src/portfolio_tracker/db/__init__.py`
- Create: `apps/api/src/portfolio_tracker/db/engine.py`
- Create: `apps/api/src/portfolio_tracker/db/models.py`
- Create: `apps/api/src/portfolio_tracker/db/session.py`
- Create: `apps/api/tests/test_db_models.py`
- Modify: `apps/api/src/portfolio_tracker/main.py` (create tables on startup)
- Modify: `apps/api/tests/conftest.py` (session fixture)

**Interfaces:**
- Consumes: `Settings.database_url`
- Produces:
  - Models: `Setting`, `Instrument`, `Transaction`, `HoldingsSnapshot`, `Price`, `BenchmarkMap`, `BenchmarkPrice` (no `metrics_cache` in v1)
  - `get_engine()`, `get_session_factory()`, `init_db()`, `get_db()` dependency yielding `Session`
  - `Setting.key` / `Setting.value` for token blob + timestamps

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_db_models.py
from portfolio_tracker.db.engine import init_db, get_session_factory
from portfolio_tracker.db.models import Instrument, Transaction


def test_can_insert_instrument_and_transaction():
    init_db()
    Session = get_session_factory()
    with Session() as session:
        inst = Instrument(
            symbol="RELIANCE",
            isin="INE002A01018",
            instrument_type="equity",
            exchange="NSE",
            mf_category=None,
        )
        session.add(inst)
        session.flush()
        tx = Transaction(
            instrument_id=inst.id,
            trade_date="2024-01-15",
            side="buy",
            quantity=10,
            price=2500.0,
            fees=20.0,
            source="csv",
            dedupe_key="csv:equity:RELIANCE:2024-01-15:buy:10:2500.0:OID1",
        )
        session.add(tx)
        session.commit()
        assert session.get(Instrument, inst.id).symbol == "RELIANCE"
        assert session.query(Transaction).count() == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && uv run pytest tests/test_db_models.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'portfolio_tracker.db'`

- [ ] **Step 3: Write minimal implementation**

```python
# apps/api/src/portfolio_tracker/db/__init__.py
from portfolio_tracker.db.engine import get_engine, get_session_factory, init_db
from portfolio_tracker.db.session import get_db

__all__ = ["get_engine", "get_session_factory", "init_db", "get_db"]
```

```python
# apps/api/src/portfolio_tracker/db/engine.py
from collections.abc import Callable
from functools import lru_cache

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session

from portfolio_tracker.config import get_settings
from portfolio_tracker.db.models import Base


@lru_cache
def get_engine() -> Engine:
    url = get_settings().database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


@lru_cache
def get_session_factory() -> Callable[[], Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())


def reset_db_cache() -> None:
    get_engine.cache_clear()
    get_session_factory.cache_clear()
```

```python
# apps/api/src/portfolio_tracker/db/models.py
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Instrument(Base):
    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    isin: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    instrument_type: Mapped[str] = mapped_column(String(16), nullable=False)  # equity|etf|mf
    exchange: Mapped[str | None] = mapped_column(String(16), nullable=True)
    mf_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mf_category_source: Mapped[str | None] = mapped_column(String(16), nullable=True)  # amfi|user|default
    yahoo_symbol: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scheme_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    needs_category: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="instrument")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (UniqueConstraint("dedupe_key", name="uq_transactions_dedupe_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), nullable=False, index=True)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    side: Mapped[str] = mapped_column(String(8), nullable=False)  # buy|sell
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    fees: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    source: Mapped[str] = mapped_column(String(8), nullable=False)  # csv|api
    dedupe_key: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    instrument: Mapped["Instrument"] = relationship(back_populates="transactions")


class HoldingsSnapshot(Base):
    __tablename__ = "holdings_snapshot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), nullable=False, unique=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    avg_price: Mapped[float] = mapped_column(Float, nullable=False)
    as_of: Mapped[str] = mapped_column(String(10), nullable=False)


class Price(Base):
    __tablename__ = "prices"
    __table_args__ = (UniqueConstraint("symbol", "price_date", name="uq_prices_symbol_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    price_date: Mapped[str] = mapped_column(String(10), nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)  # yahoo|amfi


class BenchmarkMap(Base):
    __tablename__ = "benchmark_map"

    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), primary_key=True)
    benchmark_index: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)  # default|user


class BenchmarkPrice(Base):
    __tablename__ = "benchmark_prices"
    __table_args__ = (UniqueConstraint("index_symbol", "price_date", name="uq_benchmark_prices"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    index_symbol: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    price_date: Mapped[str] = mapped_column(String(10), nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)


```

```python
# apps/api/src/portfolio_tracker/db/session.py
from collections.abc import Iterator

from sqlalchemy.orm import Session

from portfolio_tracker.db.engine import get_session_factory


def get_db() -> Iterator[Session]:
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

Update `conftest.py` to clear engine cache and call `init_db()`:

```python
# append to apps/api/tests/conftest.py (replace previous fixture body accordingly)
@pytest.fixture(autouse=True)
def _test_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("KITE_API_KEY", "test_key")
    monkeypatch.setenv("KITE_API_SECRET", "test_secret")
    monkeypatch.setenv("KITE_REDIRECT_URL", "http://127.0.0.1:8000/auth/callback")
    from portfolio_tracker.config import get_settings
    from portfolio_tracker.db.engine import init_db, reset_db_cache

    get_settings.cache_clear()
    reset_db_cache()
    init_db()
    yield
    get_settings.cache_clear()
    reset_db_cache()
```

Update `create_app()` to call `init_db()` on startup via lifespan:

```python
# in main.py
from contextlib import asynccontextmanager
from portfolio_tracker.db.engine import init_db

@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield

def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Portfolio Tracker API", version="0.1.0", lifespan=lifespan)
    # ... rest unchanged
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/api && uv run pytest tests/test_db_models.py tests/test_health.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/portfolio_tracker/db apps/api/tests/test_db_models.py apps/api/tests/conftest.py apps/api/src/portfolio_tracker/main.py
git commit -m "feat: add SQLite schema and session helpers"
```

---

### Task 3: Kite auth (login URL, token exchange, local persistence)

**Files:**
- Create: `apps/api/src/portfolio_tracker/modules/kite_auth.py`
- Create: `apps/api/src/portfolio_tracker/routers/auth.py`
- Create: `apps/api/src/portfolio_tracker/schemas/common.py`
- Create: `apps/api/tests/test_kite_auth.py`
- Modify: `apps/api/src/portfolio_tracker/main.py` (include auth router)

**Interfaces:**
- Consumes: `Settings`, `Setting` table, `Session`
- Produces:
  - `get_login_url() -> str`
  - `exchange_request_token(session, request_token: str) -> dict` (stores access_token; never returns secret)
  - `get_access_token(session) -> str | None`
  - `is_token_valid(session) -> bool` (true iff access token present; reconnect also triggered when Kite calls raise auth errors)
  - `clear_token(session) -> None`
  - `GET /auth/login-url` → `{"login_url": "..."}`
  - `POST /auth/callback` body `{"request_token": "..."}` → `{"connected": true}` (no token in body)
  - `GET /auth/status` → `{"connected": bool, "last_sync_at": str | null}`
  - Setting keys: `kite_access_token`, `kite_token_updated_at`, `last_sync_at`, `last_trade_append_at`
  - Public settings helpers (used by sync/reconcile — **not** private `_` APIs):
    - `get_setting(session, key: str) -> str | None`
    - `set_setting(session, key: str, value: str) -> None`

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_kite_auth.py
from unittest.mock import MagicMock, patch

from portfolio_tracker.db.engine import get_session_factory
from portfolio_tracker.modules import kite_auth


def test_exchange_stores_token_without_exposing_secret():
    Session = get_session_factory()
    with Session() as session:
        fake_kite = MagicMock()
        fake_kite.generate_session.return_value = {
            "access_token": "secret_access_token",
            "login_time": "2026-08-01 09:00:00",
        }
        with patch.object(kite_auth, "_build_kite", return_value=fake_kite):
            result = kite_auth.exchange_request_token(session, "req_tok")
        session.commit()
        assert result == {"connected": True}
        assert kite_auth.get_access_token(session) == "secret_access_token"
        assert kite_auth.is_token_valid(session) is True


def test_missing_credentials_login_url_raises():
    from portfolio_tracker.config import get_settings

    get_settings.cache_clear()
    import os

    os.environ["KITE_API_KEY"] = ""
    get_settings.cache_clear()
    try:
        raised = False
        try:
            kite_auth.get_login_url()
        except kite_auth.KiteConfigError:
            raised = True
        assert raised
    finally:
        os.environ["KITE_API_KEY"] = "test_key"
        get_settings.cache_clear()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && uv run pytest tests/test_kite_auth.py -v`

Expected: FAIL with import error for `kite_auth`

- [ ] **Step 3: Write minimal implementation**

```python
# apps/api/src/portfolio_tracker/modules/__init__.py
"""Domain modules."""
```

```python
# apps/api/src/portfolio_tracker/modules/kite_auth.py
from __future__ import annotations

from datetime import datetime, timezone

from kiteconnect import KiteConnect
from sqlalchemy.orm import Session

from portfolio_tracker.config import get_settings
from portfolio_tracker.db.models import Setting

TOKEN_KEY = "kite_access_token"
TOKEN_UPDATED_KEY = "kite_token_updated_at"
LAST_SYNC_KEY = "last_sync_at"
LAST_APPEND_KEY = "last_trade_append_at"


class KiteConfigError(Exception):
    pass


class KiteAuthError(Exception):
    pass


def _build_kite(api_key: str | None = None) -> KiteConnect:
    settings = get_settings()
    key = api_key or settings.kite_api_key
    if not key:
        raise KiteConfigError("KITE_API_KEY is not configured")
    return KiteConnect(api_key=key)


def set_setting(session: Session, key: str, value: str) -> None:
    row = session.get(Setting, key)
    if row is None:
        session.add(Setting(key=key, value=value))
    else:
        row.value = value


def get_setting(session: Session, key: str) -> str | None:
    row = session.get(Setting, key)
    return row.value if row else None


def get_login_url() -> str:
    settings = get_settings()
    if not settings.kite_api_key or not settings.kite_api_secret:
        raise KiteConfigError("Kite API credentials are not configured")
    kite = _build_kite()
    return kite.login_url()


def exchange_request_token(session: Session, request_token: str) -> dict[str, bool]:
    settings = get_settings()
    if not settings.kite_api_key or not settings.kite_api_secret:
        raise KiteConfigError("Kite API credentials are not configured")
    kite = _build_kite()
    try:
        data = kite.generate_session(request_token, api_secret=settings.kite_api_secret)
    except Exception as exc:  # kiteconnect raises varied errors
        raise KiteAuthError(str(exc)) from exc
    access_token = data["access_token"]
    set_setting(session, TOKEN_KEY, access_token)
    set_setting(session, TOKEN_UPDATED_KEY, datetime.now(timezone.utc).isoformat())
    return {"connected": True}


def get_access_token(session: Session) -> str | None:
    return get_setting(session, TOKEN_KEY)


def is_token_valid(session: Session) -> bool:
    return bool(get_access_token(session))


def clear_token(session: Session) -> None:
    for key in (TOKEN_KEY, TOKEN_UPDATED_KEY):
        row = session.get(Setting, key)
        if row is not None:
            session.delete(row)


def get_auth_status(session: Session) -> dict:
    return {
        "connected": is_token_valid(session),
        "credentials_configured": bool(get_settings().kite_api_key and get_settings().kite_api_secret),
        "last_sync_at": get_setting(session, LAST_SYNC_KEY),
        "last_trade_append_at": get_setting(session, LAST_APPEND_KEY),
    }


def authenticated_kite(session: Session) -> KiteConnect:
    token = get_access_token(session)
    if not token:
        raise KiteAuthError("Not connected to Zerodha")
    kite = _build_kite()
    kite.set_access_token(token)
    return kite
```

```python
# apps/api/src/portfolio_tracker/schemas/common.py
from pydantic import BaseModel


class RequestTokenBody(BaseModel):
    request_token: str


class MessageResponse(BaseModel):
    message: str
```

```python
# apps/api/src/portfolio_tracker/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from portfolio_tracker.db.session import get_db
from portfolio_tracker.modules import kite_auth
from portfolio_tracker.schemas.common import RequestTokenBody

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login-url")
def login_url() -> dict[str, str]:
    try:
        return {"login_url": kite_auth.get_login_url()}
    except kite_auth.KiteConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/callback")
def callback(body: RequestTokenBody, session: Session = Depends(get_db)) -> dict[str, bool]:
    try:
        return kite_auth.exchange_request_token(session, body.request_token)
    except kite_auth.KiteConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except kite_auth.KiteAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("/status")
def status(session: Session = Depends(get_db)) -> dict:
    return kite_auth.get_auth_status(session)


@router.post("/logout")
def logout(session: Session = Depends(get_db)) -> dict[str, bool]:
    kite_auth.clear_token(session)
    return {"connected": False}
```

Include `auth.router` in `create_app()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/api && uv run pytest tests/test_kite_auth.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/portfolio_tracker/modules/kite_auth.py apps/api/src/portfolio_tracker/routers/auth.py apps/api/src/portfolio_tracker/schemas apps/api/tests/test_kite_auth.py apps/api/src/portfolio_tracker/main.py
git commit -m "feat: add Kite OAuth login and local token storage"
```

---

### Task 4: CSV import (Console equity + Console MF tradebook, idempotent)

**Preflight:** Before trusting fixtures, compare headers to a real Console Equity + Mutual Funds tradebook export (Reports → Tradebook). If columns differ (spaces, `trade date` vs `trade_date`, etc.), update fixtures + `_norm_headers` mapping — do not invent production headers.

**Files:**
- Create: `apps/api/src/portfolio_tracker/modules/csv_import.py`
- Create: `apps/api/src/portfolio_tracker/routers/import_.py`
- Create: `apps/api/tests/fixtures/equity_tradebook.csv`
- Create: `apps/api/tests/fixtures/mf_tradebook.csv`
- Create: `apps/api/tests/test_csv_import.py`
- Modify: `apps/api/src/portfolio_tracker/main.py`

**Interfaces:**
- Consumes: `Session`, `Instrument`, `Transaction`
- Produces:
  - `detect_format(headers: list[str]) -> Literal["console_tradebook"]` — both equity and MF use Console tradebook columns; raise `CsvFormatError` if unknown
  - `import_csv(session, text: str) -> ImportResult` where
    `ImportResult = {format, new, existing, segment_counts: dict[str,int], flagged_rows: list[str], date_min, date_max}`
  - Row asset type from `segment`: `EQ` → equity/etf, `MF` → mf; other segments still imported in v1 but listed in `flagged_rows` / counted in `segment_counts` (filter decision deferred)
  - ETF heuristic: `EQ` segment and symbol/series suggests ETF → `instrument_type=etf`
  - All-or-nothing: parse+validate entire file before any write; on failure raise `CsvParseError` with report
  - Dedupe via `Transaction.dedupe_key`
  - `POST /import/csv` multipart file → ImportResult JSON
  - `get_or_create_instrument(...)` public helper for sync module

- [ ] **Step 1: Write fixtures + failing tests**

```csv
# apps/api/tests/fixtures/equity_tradebook.csv
symbol,isin,trade_date,exchange,segment,series,trade_type,auction,quantity,price,trade_id,order_id,order_execution_time
RELIANCE,INE002A01018,2024-01-15,NSE,EQ,EQ,buy,,10,2500.00,T1,O1,2024-01-15 10:00:00
INFY,INE009A01021,2024-02-01,NSE,EQ,EQ,buy,,5,1500.00,T2,O2,2024-02-01 11:00:00
```

```csv
# apps/api/tests/fixtures/mf_tradebook.csv
symbol,isin,trade_date,exchange,segment,series,trade_type,auction,quantity,price,trade_id,order_id,order_execution_time
INF090I01239,INF090I01239,2024-03-01,BSE,MF,,buy,,100.5,99.50,T3,O3,2024-03-01 09:00:00
```

```python
# apps/api/tests/test_csv_import.py
from pathlib import Path

from portfolio_tracker.db.engine import get_session_factory
from portfolio_tracker.db.models import Instrument, Transaction
from portfolio_tracker.modules import csv_import

FIXTURES = Path(__file__).parent / "fixtures"


def test_import_equity_tradebook_inserts_rows():
    text = (FIXTURES / "equity_tradebook.csv").read_text()
    Session = get_session_factory()
    with Session() as session:
        result = csv_import.import_csv(session, text)
        session.commit()
        assert result["format"] == "console_tradebook"
        assert result["new"] == 2
        assert result["existing"] == 0
        assert result["segment_counts"]["EQ"] == 2
        assert session.query(Transaction).count() == 2


def test_reimport_is_idempotent():
    text = (FIXTURES / "equity_tradebook.csv").read_text()
    Session = get_session_factory()
    with Session() as session:
        csv_import.import_csv(session, text)
        session.commit()
        result = csv_import.import_csv(session, text)
        session.commit()
        assert result["new"] == 0
        assert result["existing"] == 2
        assert session.query(Transaction).count() == 2


def test_unknown_format_rejected():
    raised = False
    try:
        csv_import.detect_format(["foo", "bar"])
    except csv_import.CsvFormatError:
        raised = True
    assert raised


def test_mf_tradebook_import():
    text = (FIXTURES / "mf_tradebook.csv").read_text()
    Session = get_session_factory()
    with Session() as session:
        result = csv_import.import_csv(session, text)
        session.commit()
        assert result["format"] == "console_tradebook"
        assert result["segment_counts"]["MF"] == 1
        assert result["new"] == 1
        inst = session.query(Instrument).one()
        assert inst.instrument_type == "mf"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && uv run pytest tests/test_csv_import.py -v`

Expected: FAIL (module missing)

- [ ] **Step 3: Write minimal implementation**

```python
# apps/api/src/portfolio_tracker/modules/csv_import.py
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from portfolio_tracker.db.models import Instrument, Transaction

FormatName = Literal["console_tradebook"]

CONSOLE_REQUIRED = {"symbol", "trade_date", "trade_type", "quantity", "price"}
# isin/segment optional in header set but expected when present


class CsvFormatError(Exception):
    pass


class CsvParseError(Exception):
    def __init__(self, message: str, errors: list[str] | None = None):
        super().__init__(message)
        self.errors = errors or []


@dataclass
class ParsedRow:
    symbol: str
    isin: str | None
    instrument_type: str
    exchange: str | None
    segment: str
    trade_date: str
    side: str
    quantity: float
    price: float
    fees: float
    order_id: str | None
    dedupe_key: str
    flagged: bool
    flag_reason: str | None


def _norm_headers(headers: list[str]) -> list[str]:
    return [h.strip().lower().replace(" ", "_") for h in headers]


def detect_format(headers: list[str]) -> FormatName:
    h = set(_norm_headers(headers))
    if CONSOLE_REQUIRED.issubset(h):
        return "console_tradebook"
    raise CsvFormatError(
        "Unrecognized CSV. Expected Zerodha Console tradebook "
        "(Reports → Tradebook → Equity or Mutual Funds)."
    )


def _parse_side(value: str) -> str:
    v = value.strip().lower()
    if v in {"buy", "b"}:
        return "buy"
    if v in {"sell", "s"}:
        return "sell"
    raise ValueError(f"Unknown trade side: {value}")


def _instrument_type(segment: str, symbol: str, series: str) -> tuple[str, bool, str | None]:
    seg = segment.strip().upper()
    if seg == "MF":
        return "mf", False, None
    if seg in {"", "EQ"}:
        if "ETF" in symbol.upper() or series.strip().upper() in {"EQ", ""}:
            # EQ is normal equity; ETF often still segment EQ — heuristic on name
            if "ETF" in symbol.upper():
                return "etf", False, None
            return "equity", False, None
        return "equity", False, None
    return "equity", True, f"unexpected segment {seg}"


def get_or_create_instrument(
    session: Session,
    *,
    symbol: str,
    isin: str | None,
    instrument_type: str,
    exchange: str | None,
) -> Instrument:
    if isin:
        inst = (
            session.query(Instrument)
            .filter((Instrument.isin == isin) | (Instrument.symbol == symbol))
            .first()
        )
    else:
        inst = session.query(Instrument).filter(Instrument.symbol == symbol).first()
    if inst:
        return inst
    yahoo = None
    if instrument_type in {"equity", "etf"}:
        yahoo = f"{symbol}.NS"  # .BO fallback at price refresh
    inst = Instrument(
        symbol=symbol,
        isin=isin,
        instrument_type=instrument_type,
        exchange=exchange,
        yahoo_symbol=yahoo,
    )
    session.add(inst)
    session.flush()
    return inst


def _parse_console_rows(rows: list[dict[str, str]]) -> tuple[list[ParsedRow], dict[str, int], list[str]]:
    parsed: list[ParsedRow] = []
    errors: list[str] = []
    segment_counts: dict[str, int] = {}
    flagged_rows: list[str] = []
    for i, row in enumerate(rows, start=2):
        try:
            symbol = row["symbol"].strip().upper()
            side = _parse_side(row["trade_type"])
            qty = float(row["quantity"])
            price = float(row["price"])
            trade_date = row["trade_date"].strip()[:10]
            segment = (row.get("segment") or "EQ").strip().upper() or "EQ"
            series = row.get("series") or ""
            order_id = (row.get("order_id") or row.get("trade_id") or "").strip() or None
            instrument_type, flagged, reason = _instrument_type(segment, symbol, series)
            segment_counts[segment] = segment_counts.get(segment, 0) + 1
            if flagged and reason:
                flagged_rows.append(f"row {i}: {symbol} {reason}")
            dedupe = f"csv:{segment}:{symbol}:{trade_date}:{side}:{qty}:{price}:{order_id or i}"
            parsed.append(
                ParsedRow(
                    symbol=symbol,
                    isin=(row.get("isin") or "").strip() or None,
                    instrument_type=instrument_type,
                    exchange=(row.get("exchange") or "").strip() or None,
                    segment=segment,
                    trade_date=trade_date,
                    side=side,
                    quantity=qty,
                    price=price,
                    fees=float(row.get("fees") or 0),
                    order_id=order_id,
                    dedupe_key=dedupe,
                    flagged=flagged,
                    flag_reason=reason,
                )
            )
        except Exception as exc:
            errors.append(f"row {i}: {exc}")
    if errors:
        raise CsvParseError("Console tradebook parse failed", errors)
    return parsed, segment_counts, flagged_rows


def import_csv(session: Session, text: str) -> dict:
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise CsvFormatError("CSV has no headers")
    fmt = detect_format(list(reader.fieldnames))
    raw_rows = [{_norm_headers([k])[0]: (v or "") for k, v in row.items()} for row in reader]
    parsed, segment_counts, flagged_rows = _parse_console_rows(raw_rows)

    new = 0
    existing = 0
    dates: list[str] = []
    for row in parsed:
        dates.append(row.trade_date)
        found = session.query(Transaction).filter(Transaction.dedupe_key == row.dedupe_key).first()
        if found:
            existing += 1
            continue
        inst = get_or_create_instrument(
            session,
            symbol=row.symbol,
            isin=row.isin,
            instrument_type=row.instrument_type,
            exchange=row.exchange,
        )
        session.add(
            Transaction(
                instrument_id=inst.id,
                trade_date=row.trade_date,
                side=row.side,
                quantity=row.quantity,
                price=row.price,
                fees=row.fees,
                source="csv",
                dedupe_key=row.dedupe_key,
                raw_order_id=row.order_id,
            )
        )
        new += 1
    return {
        "format": fmt,
        "new": new,
        "existing": existing,
        "segment_counts": segment_counts,
        "flagged_rows": flagged_rows,
        "date_min": min(dates) if dates else None,
        "date_max": max(dates) if dates else None,
    }
```

```python
# apps/api/src/portfolio_tracker/routers/import_.py
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from portfolio_tracker.db.session import get_db
from portfolio_tracker.modules import csv_import

router = APIRouter(prefix="/import", tags=["import"])


@router.post("/csv")
async def import_csv_endpoint(
    file: UploadFile = File(...),
    session: Session = Depends(get_db),
) -> dict:
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="File must be UTF-8 CSV") from exc
    try:
        return csv_import.import_csv(session, text)
    except csv_import.CsvFormatError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except csv_import.CsvParseError as exc:
        raise HTTPException(
            status_code=400,
            detail={"message": str(exc), "errors": exc.errors},
        ) from exc
```

Include `import_.router` in `create_app()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/api && uv run pytest tests/test_csv_import.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/portfolio_tracker/modules/csv_import.py apps/api/src/portfolio_tracker/routers/import_.py apps/api/tests/fixtures apps/api/tests/test_csv_import.py apps/api/src/portfolio_tracker/main.py
git commit -m "feat: import Console equity and MF tradebook CSVs"
```

---

### Task 5: Price providers (Yahoo + AMFI) + cache

**Files:**
- Create: `apps/api/src/portfolio_tracker/modules/prices/base.py`
- Create: `apps/api/src/portfolio_tracker/modules/prices/yahoo.py`
- Create: `apps/api/src/portfolio_tracker/modules/prices/amfi.py`
- Create: `apps/api/src/portfolio_tracker/modules/prices/service.py`
- Create: `apps/api/src/portfolio_tracker/modules/prices/__init__.py`
- Create: `apps/api/tests/fixtures/amfi_sample.json`
- Create: `apps/api/tests/test_prices.py`

**Interfaces:**
- Consumes: `Session`, `Instrument`, `Price`, `BenchmarkPrice`
- Produces:
  - Protocol `PriceProvider` with `get_history(symbol: str, start: str, end: str) -> list[tuple[str, float]]` and `get_ltp(symbol: str) -> float | None`
  - `YahooFinanceProvider`, `AmfiNavProvider`
  - `refresh_prices(session, as_of: str | None = None) -> PriceRefreshResult` (`updated`, `failed`, `incomplete: bool`)
  - Locked Yahoo index tickers:
    - Nifty 500 → `^CRSLDX`
    - Nifty 100 → `^CNX100`
    - Nifty Midcap 150 → `NIFTYMIDCAP150.NS`
    - Nifty Smallcap 250 → `NIFTYSMLCAP250.NS`
    - Nifty 50 → `^NSEI`
  - Equity yahoo symbol: use `Instrument.yahoo_symbol` if set; else try `{SYMBOL}.NS` then `{SYMBOL}.BO` on empty history / missing LTP; persist winner on `Instrument.yahoo_symbol`
  - MF: match ISIN / scheme_code via AMFI
  - Prefer incremental refresh: backfill history once from `history_start`; on later syncs upsert recent/LTP (avoid full 2018→today download every sync)

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_prices.py
from unittest.mock import MagicMock

from portfolio_tracker.db.engine import get_session_factory
from portfolio_tracker.db.models import Instrument, Price
from portfolio_tracker.modules.prices import service as price_service
from portfolio_tracker.modules.prices.yahoo import YahooFinanceProvider
from portfolio_tracker.modules.prices.amfi import AmfiNavProvider


def test_yahoo_provider_maps_history():
    provider = YahooFinanceProvider(client=MagicMock())
    provider._fetch_history = MagicMock(  # type: ignore[method-assign]
        return_value=[("2024-01-15", 2500.0), ("2024-01-16", 2510.0)]
    )
    rows = provider.get_history("RELIANCE.NS", "2024-01-15", "2024-01-16")
    assert rows[0] == ("2024-01-15", 2500.0)


def test_amfi_provider_resolves_isin():
    sample = {
        "meta": {"scheme_name": "Flexi Cap Fund", "scheme_category": "Equity Scheme - Flexi Cap Fund"},
        "data": [{"date": "01-03-2024", "nav": "99.50"}],
    }
    provider = AmfiNavProvider(
        http_get=MagicMock(
            side_effect=[
                [{"schemeCode": "123"}],  # ISIN search
                sample,  # scheme NAV payload
            ]
        )
    )
    rows = provider.get_history_by_isin("INF090I01239", "2024-03-01", "2024-03-01")
    assert rows == [("2024-03-01", 99.50)]


def test_refresh_prices_caches_equity_and_mf():
    Session = get_session_factory()
    with Session() as session:
        eq = Instrument(symbol="RELIANCE", isin="INE002A01018", instrument_type="equity", exchange="NSE", yahoo_symbol="RELIANCE.NS")
        mf = Instrument(symbol="INF090I01239", isin="INF090I01239", instrument_type="mf", exchange=None)
        session.add_all([eq, mf])
        session.commit()

        yahoo = MagicMock(spec=YahooFinanceProvider)
        yahoo.get_ltp.return_value = 2600.0
        yahoo.get_history.return_value = [("2024-01-15", 2500.0)]
        amfi = MagicMock(spec=AmfiNavProvider)
        amfi.get_ltp_by_isin.return_value = 100.0
        amfi.get_history_by_isin.return_value = [("2024-03-01", 99.5)]
        amfi.resolve_category.return_value = ("Flexi Cap", "123")

        result = price_service.refresh_prices(
            session, as_of="2024-06-01", yahoo=yahoo, amfi=amfi, history_start="2024-01-01"
        )
        session.commit()
        assert result["incomplete"] is False
        assert session.query(Price).count() >= 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && uv run pytest tests/test_prices.py -v`

Expected: FAIL (module missing)

- [ ] **Step 3: Write minimal implementation**

```python
# apps/api/src/portfolio_tracker/modules/prices/base.py
from typing import Protocol


class PriceProvider(Protocol):
    def get_history(self, symbol: str, start: str, end: str) -> list[tuple[str, float]]: ...

    def get_ltp(self, symbol: str) -> float | None: ...
```

```python
# apps/api/src/portfolio_tracker/modules/prices/yahoo.py
from __future__ import annotations

from datetime import datetime

import yfinance as yf

INDEX_TICKERS: dict[str, str] = {
    "Nifty 500": "^CRSLDX",
    "Nifty 100": "^CNX100",
    "Nifty Midcap 150": "NIFTYMIDCAP150.NS",
    "Nifty Smallcap 250": "NIFTYSMLCAP250.NS",
    "Nifty 50": "^NSEI",
}


class YahooFinanceProvider:
    def __init__(self, client=None):
        self._client = client  # optional injectable for tests

    def _fetch_history(self, symbol: str, start: str, end: str) -> list[tuple[str, float]]:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start, end=end, auto_adjust=True)
        if df is None or df.empty:
            return []
        rows: list[tuple[str, float]] = []
        for idx, row in df.iterrows():
            day = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]
            rows.append((day, float(row["Close"])))
        return rows

    def get_history(self, symbol: str, start: str, end: str) -> list[tuple[str, float]]:
        return self._fetch_history(symbol, start, end)

    def get_ltp(self, symbol: str) -> float | None:
        rows = self.get_history(symbol, start=(datetime.utcnow().date().isoformat()), end=None)  # type: ignore[arg-type]
        # Prefer fast_info last price
        try:
            info = yf.Ticker(symbol).fast_info
            last = getattr(info, "last_price", None)
            if last is not None:
                return float(last)
        except Exception:
            pass
        hist = self.get_history(symbol, start="2020-01-01", end=datetime.utcnow().date().isoformat())
        return hist[-1][1] if hist else None
```

Fix `get_ltp` properly in implementation — do not pass `end=None` to history:

```python
    def get_ltp(self, symbol: str) -> float | None:
        try:
            info = yf.Ticker(symbol).fast_info
            last = getattr(info, "last_price", None)
            if last is not None:
                return float(last)
        except Exception:
            pass
        end = datetime.utcnow().date().isoformat()
        hist = self.get_history(symbol, start="2020-01-01", end=end)
        return hist[-1][1] if hist else None
```

```python
# apps/api/src/portfolio_tracker/modules/prices/amfi.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

import httpx

HttpGet = Callable[[str], Any]


def _parse_nav_date(value: str) -> str:
    # mfapi returns DD-MM-YYYY
    return datetime.strptime(value, "%d-%m-%Y").strftime("%Y-%m-%d")


class AmfiNavProvider:
    def __init__(self, http_get: HttpGet | None = None):
        self._http_get = http_get or self._default_get

    def _default_get(self, url: str) -> Any:
        response = httpx.get(url, timeout=30.0)
        response.raise_for_status()
        return response.json()

    def _scheme_payload(self, scheme_code: str) -> dict:
        return self._http_get(f"https://api.mfapi.in/mf/{scheme_code}")

    def find_scheme_code_by_isin(self, isin: str) -> str | None:
        # mfapi search
        data = self._http_get(f"https://api.mfapi.in/mf/search?q={isin}")
        if isinstance(data, list) and data:
            return str(data[0].get("schemeCode") or data[0].get("scheme_code"))
        return None

    def get_history_by_isin(self, isin: str, start: str, end: str) -> list[tuple[str, float]]:
        code = self.find_scheme_code_by_isin(isin) or isin
        # tests inject payload directly via http_get for scheme URL; support both
        payload = self._http_get(f"https://api.mfapi.in/mf/{code}")
        if "data" not in payload and "meta" not in payload:
            # test injected sample already
            payload = payload if isinstance(payload, dict) else {}
        rows: list[tuple[str, float]] = []
        for item in payload.get("data", []):
            day = _parse_nav_date(item["date"])
            if start <= day <= end:
                rows.append((day, float(item["nav"])))
        rows.sort(key=lambda r: r[0])
        return rows

    def get_ltp_by_isin(self, isin: str) -> float | None:
        end = datetime.utcnow().date().isoformat()
        rows = self.get_history_by_isin(isin, "2000-01-01", end)
        return rows[-1][1] if rows else None

    def resolve_category(self, isin: str) -> tuple[str | None, str | None]:
        code = self.find_scheme_code_by_isin(isin)
        if not code:
            return None, None
        payload = self._scheme_payload(code)
        meta = payload.get("meta") or {}
        category = meta.get("scheme_category") or meta.get("scheme_type")
        # Normalize to bucket used by benchmarks
        normalized = None
        if category:
            lower = category.lower()
            if "flexi" in lower:
                normalized = "Flexi Cap"
            elif "large" in lower and "mid" not in lower:
                normalized = "Large Cap"
            elif "mid" in lower:
                normalized = "Mid Cap"
            elif "small" in lower:
                normalized = "Small Cap"
            else:
                normalized = category
        return normalized, code
```

```python
# apps/api/src/portfolio_tracker/modules/prices/service.py
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from portfolio_tracker.db.models import Instrument, Price, BenchmarkPrice
from portfolio_tracker.modules.prices.amfi import AmfiNavProvider
from portfolio_tracker.modules.prices.yahoo import INDEX_TICKERS, YahooFinanceProvider


def _upsert_price(session: Session, symbol: str, price_date: str, close: float, source: str) -> None:
    row = (
        session.query(Price)
        .filter(Price.symbol == symbol, Price.price_date == price_date)
        .first()
    )
    if row:
        row.close = close
        row.source = source
    else:
        session.add(Price(symbol=symbol, price_date=price_date, close=close, source=source))


def _upsert_benchmark(session: Session, index_symbol: str, price_date: str, close: float) -> None:
    row = (
        session.query(BenchmarkPrice)
        .filter(BenchmarkPrice.index_symbol == index_symbol, BenchmarkPrice.price_date == price_date)
        .first()
    )
    if row:
        row.close = close
    else:
        session.add(BenchmarkPrice(index_symbol=index_symbol, price_date=price_date, close=close))


def refresh_prices(
    session: Session,
    *,
    as_of: str | None = None,
    history_start: str = "2018-01-01",
    yahoo: YahooFinanceProvider | None = None,
    amfi: AmfiNavProvider | None = None,
    benchmark_names: list[str] | None = None,
) -> dict:
    yahoo = yahoo or YahooFinanceProvider()
    amfi = amfi or AmfiNavProvider()
    as_of = as_of or date.today().isoformat()
    updated = 0
    failed: list[str] = []

    instruments = session.query(Instrument).all()
    for inst in instruments:
        try:
            if inst.instrument_type == "mf":
                isin = inst.isin or inst.symbol
                hist = amfi.get_history_by_isin(isin, history_start, as_of)
                for day, close in hist:
                    _upsert_price(session, isin, day, close, "amfi")
                    updated += 1
                category, scheme_code = amfi.resolve_category(isin)
                if scheme_code:
                    inst.scheme_code = scheme_code
                if category and inst.mf_category_source != "user":
                    inst.mf_category = category
                    inst.mf_category_source = "amfi"
                    inst.needs_category = 0
                elif not inst.mf_category:
                    inst.needs_category = 1
            else:
                candidates = []
                if inst.yahoo_symbol:
                    candidates.append(inst.yahoo_symbol)
                for suffix in (".NS", ".BO"):
                    candidate = f"{inst.symbol}{suffix}"
                    if candidate not in candidates:
                        candidates.append(candidate)
                hist: list[tuple[str, float]] = []
                chosen: str | None = None
                for symbol in candidates:
                    hist = yahoo.get_history(symbol, history_start, as_of)
                    if hist:
                        chosen = symbol
                        break
                if chosen is None:
                    raise RuntimeError("no Yahoo history for .NS or .BO")
                inst.yahoo_symbol = chosen
                for day, close in hist:
                    _upsert_price(session, chosen, day, close, "yahoo")
                    updated += 1
                ltp = yahoo.get_ltp(chosen)
                if ltp is not None:
                    _upsert_price(session, chosen, as_of, ltp, "yahoo")
                    updated += 1
        except Exception as exc:
            failed.append(f"{inst.symbol}: {exc}")

    names = benchmark_names or list(INDEX_TICKERS.keys())
    for name in names:
        ticker = INDEX_TICKERS[name]
        try:
            for day, close in yahoo.get_history(ticker, history_start, as_of):
                _upsert_benchmark(session, name, day, close)
                updated += 1
        except Exception as exc:
            failed.append(f"benchmark {name}: {exc}")

    return {"updated": updated, "failed": failed, "incomplete": bool(failed)}
```

```python
# apps/api/src/portfolio_tracker/modules/prices/__init__.py
from portfolio_tracker.modules.prices.service import refresh_prices
from portfolio_tracker.modules.prices.yahoo import INDEX_TICKERS, YahooFinanceProvider
from portfolio_tracker.modules.prices.amfi import AmfiNavProvider

__all__ = ["refresh_prices", "INDEX_TICKERS", "YahooFinanceProvider", "AmfiNavProvider"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/api && uv run pytest tests/test_prices.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/portfolio_tracker/modules/prices apps/api/tests/test_prices.py apps/api/tests/fixtures/amfi_sample.json
git commit -m "feat: add Yahoo Finance and AMFI price providers with DB cache"
```

---

### Task 6: Benchmark mapping + defaults

**Files:**
- Create: `apps/api/src/portfolio_tracker/modules/benchmarks.py`
- Create: `apps/api/tests/test_benchmarks.py`

**Interfaces:**
- Consumes: `Instrument`, `BenchmarkMap`, `Session`
- Produces:
  - `DEFAULT_BY_CATEGORY: dict[str, str]` per spec table
  - `default_benchmark_for(instrument: Instrument) -> str`
  - `ensure_benchmark_map(session, instrument) -> BenchmarkMap` (does not overwrite `source=="user"`)
  - `set_benchmark_override(session, instrument_id: int, benchmark_index: str) -> BenchmarkMap`
  - `set_category_override(session, instrument_id: int, category: str) -> Instrument` (also refreshes default benchmark if not user-overridden)
  - `portfolio_blended_benchmark_return(weights_and_returns: list[tuple[float, float]]) -> float` — value-weighted average of each holding’s benchmark return

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_benchmarks.py
from portfolio_tracker.db.engine import get_session_factory
from portfolio_tracker.db.models import Instrument
from portfolio_tracker.modules import benchmarks


def test_default_benchmark_by_category():
    mid = Instrument(symbol="X", instrument_type="mf", mf_category="Mid Cap")
    assert benchmarks.default_benchmark_for(mid) == "Nifty Midcap 150"
    eq = Instrument(symbol="RELIANCE", instrument_type="equity")
    assert benchmarks.default_benchmark_for(eq) == "Nifty 500"
    unknown = Instrument(symbol="Y", instrument_type="mf", mf_category=None)
    assert benchmarks.default_benchmark_for(unknown) == "Nifty 500"


def test_user_override_wins():
    Session = get_session_factory()
    with Session() as session:
        inst = Instrument(symbol="RELIANCE", instrument_type="equity", exchange="NSE")
        session.add(inst)
        session.flush()
        benchmarks.ensure_benchmark_map(session, inst)
        benchmarks.set_benchmark_override(session, inst.id, "Nifty 50")
        session.commit()
        row = benchmarks.ensure_benchmark_map(session, inst)
        assert row.benchmark_index == "Nifty 50"
        assert row.source == "user"


def test_value_weighted_blend():
    # weights 0.7 and 0.3, returns 10% and 20% → 13%
    assert abs(benchmarks.portfolio_blended_benchmark_return([(0.7, 0.10), (0.3, 0.20)]) - 0.13) < 1e-9
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && uv run pytest tests/test_benchmarks.py -v`

Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# apps/api/src/portfolio_tracker/modules/benchmarks.py
from __future__ import annotations

from sqlalchemy.orm import Session

from portfolio_tracker.db.models import BenchmarkMap, Instrument

DEFAULT_BY_CATEGORY: dict[str, str] = {
    "Flexi Cap": "Nifty 500",
    "Large Cap": "Nifty 100",
    "Mid Cap": "Nifty Midcap 150",
    "Small Cap": "Nifty Smallcap 250",
}


def default_benchmark_for(instrument: Instrument) -> str:
    if instrument.instrument_type == "mf":
        if instrument.mf_category and instrument.mf_category in DEFAULT_BY_CATEGORY:
            return DEFAULT_BY_CATEGORY[instrument.mf_category]
        return "Nifty 500"
    # stocks / unknown ETFs
    if instrument.instrument_type == "etf" and instrument.mf_category:
        # optional: underlying index name stored in mf_category for index ETFs
        return instrument.mf_category
    return "Nifty 500"


def ensure_benchmark_map(session: Session, instrument: Instrument) -> BenchmarkMap:
    row = session.get(BenchmarkMap, instrument.id)
    if row is None:
        row = BenchmarkMap(
            instrument_id=instrument.id,
            benchmark_index=default_benchmark_for(instrument),
            source="default",
        )
        session.add(row)
        session.flush()
        if instrument.instrument_type == "mf" and not instrument.mf_category:
            instrument.needs_category = 1
        return row
    if row.source != "user":
        row.benchmark_index = default_benchmark_for(instrument)
        row.source = "default"
    return row


def set_benchmark_override(session: Session, instrument_id: int, benchmark_index: str) -> BenchmarkMap:
    row = session.get(BenchmarkMap, instrument_id)
    if row is None:
        row = BenchmarkMap(instrument_id=instrument_id, benchmark_index=benchmark_index, source="user")
        session.add(row)
    else:
        row.benchmark_index = benchmark_index
        row.source = "user"
    session.flush()
    return row


def set_category_override(session: Session, instrument_id: int, category: str) -> Instrument:
    inst = session.get(Instrument, instrument_id)
    if inst is None:
        raise ValueError(f"Instrument {instrument_id} not found")
    inst.mf_category = category
    inst.mf_category_source = "user"
    inst.needs_category = 0
    ensure_benchmark_map(session, inst)
    return inst


def portfolio_blended_benchmark_return(weights_and_returns: list[tuple[float, float]]) -> float:
    if not weights_and_returns:
        return 0.0
    return sum(w * r for w, r in weights_and_returns)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/api && uv run pytest tests/test_benchmarks.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/portfolio_tracker/modules/benchmarks.py apps/api/tests/test_benchmarks.py
git commit -m "feat: add category-to-benchmark defaults and overrides"
```

---

### Task 7: Metrics (absolute, CAGR, XIRR, excess, rolling windows)

**Files:**
- Create: `apps/api/src/portfolio_tracker/modules/metrics.py`
- Create: `apps/api/tests/test_metrics.py`

**Interfaces:**
- Consumes: cashflow lists, prices, `benchmarks.portfolio_blended_benchmark_return`
- Produces pure functions (no I/O):
  - `CashFlow = tuple[str, float]`  # (YYYY-MM-DD, amount) buys negative, sells positive, terminal MV positive
  - `WINDOW_DAYS = {"ITD": None, "1Y": 365, "3Y": 1095, "5Y": 1825}`  # days; ITD has no fixed length
  - `window_start(as_of: str, window: str, inception_date: str) -> str | None` — for ITD returns `inception_date`; for 1Y/3Y/5Y returns `as_of − N days` or `None` if `inception_date > that start` (insufficient history)
  - `absolute_return(invested_cost: float, current_value: float) -> dict` with `gain_inr`, `gain_pct` (`None` if cost ≤ 0)
  - `invested_cost_from_transactions(txs: list[tuple[str, float, float, float]]) -> float` where tuple is `(side, qty, price, fees)` using proportional avg-cost on sells
  - `cagr(start_value: float, end_value: float, start_date: str, end_date: str) -> float | None` — `None` if span < 365 days or start_value ≤ 0
  - `xirr(cashflows: list[CashFlow]) -> float | None`
  - `benchmark_return(start_price: float, end_price: float) -> float | None`
  - `excess_pp(portfolio_return: float, benchmark_return: float) -> float` — `(p - b) * 100` pp
  - `build_xirr_cashflows(...)` for ITD
  - `build_rolling_xirr_cashflows(opening_mv, window_start, trades_in_window, terminal_mv, as_of) -> list[CashFlow]` — if `opening_mv > 0`, prepend `(-opening_mv, window_start)`; append terminal `+terminal_mv` at `as_of`
  - `point_to_point_return(start_value: float, end_value: float) -> float | None` — `(end/start) - 1` when start > 0
  - `index_units_terminal_mv(trades, index_price_on, as_of, *, opening_mv=0.0, window_start=None) -> float | None` — same ₹ notionals buy/sell index units; optional opening_mv buys index at `window_start`
  - `benchmark_xirr_from_trades(trades, index_price_on, as_of, *, opening_mv=0.0, window_start=None) -> float | None` — XIRR of same cashflows + index terminal MV (unit-correct peer for port XIRR)
  - Window metric bundle shape: `{absolute, xirr, cagr, benchmark_return, absolute_excess_pp, xirr_excess_pp, cagr_excess_pp}` (any field may be `null`)
  - **Rolling absolute (v1):** prefer point-to-point on `opening_mv → terminal_mv` when `opening_mv > 0`; if no position at window start, fall back to ITD-style invested_cost from in-window txs only (buys/sells in window) vs terminal_mv
  - **Rolling XIRR (v1):** opening MV as synthetic buy + in-window txs + terminal MV
  - **Rolling CAGR (v1):** `cagr(opening_mv, terminal_mv, window_start, as_of)` when opening_mv > 0; else N/A
  - **Excess:** absolute vs point-to-point bench %; CAGR vs bench CAGR; XIRR vs `benchmark_xirr_from_trades` — never XIRR vs raw point-to-point

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_metrics.py
from portfolio_tracker.modules import metrics


def test_absolute_return():
    result = metrics.absolute_return(invested_cost=100_000, current_value=125_000)
    assert result["gain_inr"] == 25_000
    assert abs(result["gain_pct"] - 0.25) < 1e-9


def test_absolute_return_na_when_zero_cost():
    result = metrics.absolute_return(invested_cost=0, current_value=1000)
    assert result["gain_pct"] is None


def test_cagr_requires_365_days():
    assert metrics.cagr(100, 110, "2024-01-01", "2024-06-01") is None
    value = metrics.cagr(100, 121, "2022-01-01", "2024-01-01")
    assert value is not None
    assert abs(value - 0.1) < 1e-6


def test_xirr_simple():
    flows = [
        ("2022-01-01", -1000.0),
        ("2024-01-01", 1210.0),
    ]
    rate = metrics.xirr(flows)
    assert rate is not None
    assert abs(rate - 0.1) < 1e-3


def test_invested_cost_with_partial_sell():
    # buy 10 @ 100 fee 0 → cost 1000; sell 4 → remove 400; remaining cost 600
    cost = metrics.invested_cost_from_transactions(
        [
            ("buy", 10, 100.0, 0.0),
            ("sell", 4, 120.0, 0.0),
        ]
    )
    assert abs(cost - 600.0) < 1e-9


def test_excess_pp():
    assert abs(metrics.excess_pp(0.15, 0.10) - 5.0) < 1e-9


def test_cagr_not_suppressed_for_multi_buy_span():
    # Multiple buys do not block CAGR when span ≥ 365d — use invested_cost → MV heuristic
    assert metrics.cagr(100_000, 120_000, "2022-01-01", "2024-01-01") is not None


def test_window_start_requires_enough_history():
    # 2024-06-01 − 365d = 2023-06-02; inception 2023-06-01 → 1Y available; 3Y not
    assert metrics.window_start("2024-06-01", "1Y", "2023-06-01") == "2023-06-02"
    assert metrics.window_start("2024-06-01", "3Y", "2023-06-01") is None
    assert metrics.window_start("2024-06-01", "ITD", "2023-06-01") == "2023-06-01"


def test_rolling_xirr_includes_opening_mv():
    flows = metrics.build_rolling_xirr_cashflows(
        opening_mv=1000.0,
        window_start="2023-01-01",
        trades_in_window=[("2023-06-01", "buy", 1, 100.0, 0.0)],
        terminal_mv=1500.0,
        as_of="2024-01-01",
    )
    assert flows[0] == ("2023-01-01", -1000.0)
    assert flows[-1] == ("2024-01-01", 1500.0)


def test_benchmark_xirr_same_cashflows_not_point_to_point():
    # Buy ₹1000 of "stock" when index=100 → 10 units; as_of index=121 → terminal 1210
    prices = {"2022-01-01": 100.0, "2024-01-01": 121.0}

    def idx(day: str) -> float | None:
        return prices.get(day)

    trades = [("2022-01-01", "buy", 1, 1000.0, 0.0)]
    bx = metrics.benchmark_xirr_from_trades(trades, idx, "2024-01-01")
    assert bx is not None
    assert abs(bx - 0.1) < 1e-3
    # Must not equal a mistaken excess that compared XIRR to simple return incorrectly in callers
    assert abs(metrics.excess_pp(0.1, bx)) < 1e-6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && uv run pytest tests/test_metrics.py -v`

Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# apps/api/src/portfolio_tracker/modules/metrics.py
from __future__ import annotations

from datetime import date, datetime
from typing import Iterable

import numpy_financial as npf


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def absolute_return(invested_cost: float, current_value: float) -> dict:
    gain = current_value - invested_cost
    pct = (gain / invested_cost) if invested_cost > 0 else None
    return {"gain_inr": gain, "gain_pct": pct, "invested_cost": invested_cost, "current_value": current_value}


def invested_cost_from_transactions(txs: Iterable[tuple[str, float, float, float]]) -> float:
    qty = 0.0
    cost = 0.0
    for side, q, price, fees in txs:
        if side == "buy":
            cost += q * price + fees
            qty += q
        elif side == "sell":
            if qty <= 0:
                continue
            avg = cost / qty
            sell_q = min(q, qty)
            cost -= avg * sell_q
            qty -= sell_q
    return max(cost, 0.0)


def cagr(start_value: float, end_value: float, start_date: str, end_date: str) -> float | None:
    if start_value <= 0:
        return None
    days = (_parse_date(end_date) - _parse_date(start_date)).days
    if days < 365:
        return None
    years = days / 365.25
    return (end_value / start_value) ** (1 / years) - 1


def xirr(cashflows: list[tuple[str, float]]) -> float | None:
    if len(cashflows) < 2:
        return None
    amounts = [c[1] for c in cashflows]
    dates = [_parse_date(c[0]) for c in cashflows]
    if all(a <= 0 for a in amounts) or all(a >= 0 for a in amounts):
        return None
    try:
        rate = float(npf.xirr(amounts, dates))
    except Exception:
        return None
    if rate != rate:  # NaN
        return None
    return rate


def benchmark_return(start_price: float, end_price: float) -> float | None:
    if start_price <= 0:
        return None
    return (end_price / start_price) - 1


def excess_pp(portfolio_return: float, bench_return: float) -> float:
    return (portfolio_return - bench_return) * 100.0


def build_xirr_cashflows(
    trades: list[tuple[str, str, float, float, float]],
    terminal_value: float,
    as_of: str,
) -> list[tuple[str, float]]:
    """trades: (trade_date, side, qty, price, fees)."""
    flows: list[tuple[str, float]] = []
    for trade_date, side, qty, price, fees in trades:
        notional = qty * price
        if side == "buy":
            flows.append((trade_date, -(notional + fees)))
        else:
            flows.append((trade_date, notional - fees))
    flows.append((as_of, terminal_value))
    flows.sort(key=lambda x: x[0])
    return flows


WINDOW_DAYS: dict[str, int | None] = {"ITD": None, "1Y": 365, "3Y": 1095, "5Y": 1825}


def window_start(as_of: str, window: str, inception_date: str) -> str | None:
    if window == "ITD":
        return inception_date
    days = WINDOW_DAYS.get(window)
    if days is None:
        raise ValueError(f"Unknown window: {window}")
    start = _parse_date(as_of) - __import__("datetime").timedelta(days=days)
    start_s = start.isoformat()
    if _parse_date(inception_date) > start:
        return None
    return start_s


def point_to_point_return(start_value: float, end_value: float) -> float | None:
    if start_value <= 0:
        return None
    return (end_value / start_value) - 1


def build_rolling_xirr_cashflows(
    *,
    opening_mv: float,
    window_start: str,
    trades_in_window: list[tuple[str, str, float, float, float]],
    terminal_mv: float,
    as_of: str,
) -> list[tuple[str, float]]:
    flows: list[tuple[str, float]] = []
    if opening_mv > 0:
        flows.append((window_start, -opening_mv))
    flows.extend(
        build_xirr_cashflows(trades_in_window, terminal_value=0.0, as_of=as_of)[:-1]
    )
    flows.append((as_of, terminal_mv))
    flows.sort(key=lambda x: x[0])
    return flows


def index_units_terminal_mv(
    trades: list[tuple[str, str, float, float, float]],
    index_price_on,
    as_of: str,
    *,
    opening_mv: float = 0.0,
    window_start: str | None = None,
) -> float | None:
    """Same ₹ notionals as trades, invested in an index; return terminal MV of index units."""
    units = 0.0
    if opening_mv > 0:
        if not window_start:
            return None
        px0 = index_price_on(window_start)
        if px0 is None or px0 <= 0:
            return None
        units += opening_mv / px0
    for trade_date, side, qty, price, fees in trades:
        px = index_price_on(trade_date)
        if px is None or px <= 0:
            return None
        notional = qty * price
        if side == "buy":
            units += (notional + fees) / px
        else:
            units -= max(notional - fees, 0.0) / px
    end = index_price_on(as_of)
    if end is None or end <= 0:
        return None
    return max(units, 0.0) * end


def benchmark_xirr_from_trades(
    trades: list[tuple[str, str, float, float, float]],
    index_price_on,
    as_of: str,
    *,
    opening_mv: float = 0.0,
    window_start: str | None = None,
) -> float | None:
    terminal = index_units_terminal_mv(
        trades,
        index_price_on,
        as_of,
        opening_mv=opening_mv,
        window_start=window_start,
    )
    if terminal is None:
        return None
    if opening_mv > 0 and window_start:
        flows = build_rolling_xirr_cashflows(
            opening_mv=opening_mv,
            window_start=window_start,
            trades_in_window=trades,
            terminal_mv=terminal,
            as_of=as_of,
        )
    else:
        flows = build_xirr_cashflows(trades, terminal, as_of)
    return xirr(flows)
```

Prefer `from datetime import timedelta` at top of file instead of `__import__` hack when implementing. Type `index_price_on` as `Callable[[str], float | None]`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/api && uv run pytest tests/test_metrics.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/portfolio_tracker/modules/metrics.py apps/api/tests/test_metrics.py
git commit -m "feat: add absolute, CAGR, XIRR, and excess metric helpers"
```

---

### Task 8a: Portfolio ITD assembly (holdings + overview, no rolling yet)

**Files:**
- Create: `apps/api/src/portfolio_tracker/modules/portfolio.py`
- Create: `apps/api/src/portfolio_tracker/routers/portfolio.py`
- Create: `apps/api/tests/test_portfolio.py`
- Modify: `apps/api/src/portfolio_tracker/main.py`

**Interfaces:**
- Consumes: `HoldingsSnapshot`, `Transaction`, `Price`, `metrics.*`, `benchmarks.*`, `BenchmarkPrice`
- Produces:
  - `get_holdings(session, as_of: str) -> list[HoldingRow]` — ITD fields; `windows` may be omitted or `{"ITD": ...}` only until 8b
  - `get_overview(session, as_of: str) -> Overview` — ITD top-level fields; `windows` at least `{"ITD": bundle}`
  - Prefer `HoldingsSnapshot` qty/avg when present; cashflows from transactions only
  - HTTP: `GET /portfolio/overview`, `GET /portfolio/holdings` (mount router)
  - Recompute on every read (no metrics cache)
  - **XIRR excess:** `excess_pp(port_xirr, metrics.benchmark_xirr_from_trades(...))` — not vs point-to-point
  - **CAGR excess (instrument):** port CAGR vs bench CAGR
  - **CAGR excess (portfolio):** port CAGR vs value-weighted blend of instrument bench CAGRs

- [ ] **Step 1: Write the failing ITD test**

```python
# apps/api/tests/test_portfolio.py
from portfolio_tracker.db.engine import get_session_factory
from portfolio_tracker.db.models import (
    BenchmarkMap,
    BenchmarkPrice,
    HoldingsSnapshot,
    Instrument,
    Price,
    Transaction,
)
from portfolio_tracker.modules import portfolio


def _seed_itd(session):
    inst = Instrument(
        symbol="RELIANCE",
        isin="INE002A01018",
        instrument_type="equity",
        exchange="NSE",
        yahoo_symbol="RELIANCE.NS",
    )
    session.add(inst)
    session.flush()
    session.add(
        Transaction(
            instrument_id=inst.id,
            trade_date="2022-01-03",
            side="buy",
            quantity=10,
            price=2000.0,
            fees=0,
            source="csv",
            dedupe_key="t1",
        )
    )
    session.add(
        HoldingsSnapshot(
            instrument_id=inst.id, quantity=10, avg_price=2000.0, as_of="2024-06-01"
        )
    )
    session.add(Price(symbol="RELIANCE.NS", price_date="2022-01-03", close=2000.0, source="yahoo"))
    session.add(Price(symbol="RELIANCE.NS", price_date="2024-06-01", close=2600.0, source="yahoo"))
    session.add(BenchmarkMap(instrument_id=inst.id, benchmark_index="Nifty 500", source="default"))
    session.add(BenchmarkPrice(index_symbol="Nifty 500", price_date="2022-01-03", close=10000.0))
    session.add(BenchmarkPrice(index_symbol="Nifty 500", price_date="2024-06-01", close=12000.0))
    session.commit()
    return inst


def test_overview_itd_core_metrics():
    Session = get_session_factory()
    with Session() as session:
        _seed_itd(session)
        overview = portfolio.get_overview(session, as_of="2024-06-01")
        assert overview["total_value"] == 26000.0
        assert overview["absolute"]["gain_inr"] == 6000.0
        assert overview["xirr"] is not None
        assert overview["cagr"] is not None
        assert overview["absolute_excess_pp"] is not None
        assert overview["xirr_excess_pp"] is not None
        assert overview["cagr_excess_pp"] is not None  # blended bench CAGR path
        assert overview["windows"]["ITD"] is not None


def test_holdings_itd_xirr_excess_uses_benchmark_xirr():
    Session = get_session_factory()
    with Session() as session:
        _seed_itd(session)
        rows = portfolio.get_holdings(session, as_of="2024-06-01")
        assert len(rows) == 1
        h = rows[0]
        assert h["xirr"] is not None
        assert h["xirr_excess_pp"] is not None
        # Point-to-point bench = 20%; if someone wrongly used excess_pp(xirr, 0.20),
        # excess would be huge/wrong. Same-cashflow bench XIRR keeps |excess| modest.
        assert abs(h["xirr_excess_pp"]) < 50.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && uv run pytest tests/test_portfolio.py -v`

Expected: FAIL

- [ ] **Step 3: Implement ITD-only `portfolio.py` + router**

Price helpers and ITD assembly (ship complete; rolling stubs OK):

```python
# apps/api/src/portfolio_tracker/modules/portfolio.py
from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from portfolio_tracker.db.models import (
    BenchmarkMap,
    BenchmarkPrice,
    HoldingsSnapshot,
    Instrument,
    Price,
    Transaction,
)
from portfolio_tracker.modules import benchmarks, metrics


def _latest_price(session: Session, symbol: str, as_of: str) -> float | None:
    row = (
        session.query(Price)
        .filter(Price.symbol == symbol, Price.price_date <= as_of)
        .order_by(Price.price_date.desc())
        .first()
    )
    return row.close if row else None


def _benchmark_price(session: Session, index_name: str, as_of: str) -> float | None:
    row = (
        session.query(BenchmarkPrice)
        .filter(BenchmarkPrice.index_symbol == index_name, BenchmarkPrice.price_date <= as_of)
        .order_by(BenchmarkPrice.price_date.desc())
        .first()
    )
    return row.close if row else None


def _price_on_or_after(session: Session, index_name: str, day: str) -> float | None:
    row = (
        session.query(BenchmarkPrice)
        .filter(BenchmarkPrice.index_symbol == index_name, BenchmarkPrice.price_date >= day)
        .order_by(BenchmarkPrice.price_date.asc())
        .first()
    )
    return row.close if row else _benchmark_price(session, index_name, day)


def _instrument_price_symbol(inst: Instrument) -> str:
    if inst.instrument_type == "mf":
        return inst.isin or inst.symbol
    return inst.yahoo_symbol or f"{inst.symbol}.NS"


def _index_price_fn(session: Session, index_name: str) -> Callable[[str], float | None]:
    def _fn(day: str) -> float | None:
        return _benchmark_price(session, index_name, day) or _price_on_or_after(
            session, index_name, day
        )

    return _fn


def get_holdings(session: Session, as_of: str) -> list[dict]:
    rows: list[dict] = []
    for inst in session.query(Instrument).all():
        snap = session.query(HoldingsSnapshot).filter(HoldingsSnapshot.instrument_id == inst.id).first()
        txs = (
            session.query(Transaction)
            .filter(Transaction.instrument_id == inst.id)
            .order_by(Transaction.trade_date.asc())
            .all()
        )
        if snap:
            qty, avg = snap.quantity, snap.avg_price
        else:
            qty = 0.0
            cost = 0.0
            for t in txs:
                if t.side == "buy":
                    cost += t.quantity * t.price + t.fees
                    qty += t.quantity
                else:
                    if qty > 0:
                        avg_c = cost / qty
                        cost -= avg_c * min(t.quantity, qty)
                        qty -= min(t.quantity, qty)
            avg = (cost / qty) if qty else 0.0
        if qty <= 0 and not txs:
            continue
        px_symbol = _instrument_price_symbol(inst)
        ltp = _latest_price(session, px_symbol, as_of)
        value = (ltp * qty) if ltp is not None else None
        trade_tuples = [(t.trade_date, t.side, t.quantity, t.price, t.fees) for t in txs]
        invested = metrics.invested_cost_from_transactions(
            [(t.side, t.quantity, t.price, t.fees) for t in txs]
        )
        abs_ret = metrics.absolute_return(invested, value or 0.0)
        first_date = txs[0].trade_date if txs else as_of
        flows = metrics.build_xirr_cashflows(trade_tuples, value or 0.0, as_of)
        xirr_v = metrics.xirr(flows) if value is not None else None
        cagr_v = (
            metrics.cagr(invested, value, first_date, as_of) if value is not None else None
        )
        bmap = benchmarks.ensure_benchmark_map(session, inst)
        b_start = _price_on_or_after(session, bmap.benchmark_index, first_date)
        b_end = _benchmark_price(session, bmap.benchmark_index, as_of)
        bench_ret = metrics.benchmark_return(b_start, b_end) if b_start and b_end else None
        bench_cagr = (
            metrics.cagr(b_start, b_end, first_date, as_of) if b_start and b_end else None
        )
        bench_xirr = metrics.benchmark_xirr_from_trades(
            trade_tuples, _index_price_fn(session, bmap.benchmark_index), as_of
        )
        absolute_excess = (
            metrics.excess_pp(abs_ret["gain_pct"], bench_ret)
            if abs_ret["gain_pct"] is not None and bench_ret is not None
            else None
        )
        xirr_excess = (
            metrics.excess_pp(xirr_v, bench_xirr)
            if xirr_v is not None and bench_xirr is not None
            else None
        )
        cagr_excess = (
            metrics.excess_pp(cagr_v, bench_cagr)
            if cagr_v is not None and bench_cagr is not None
            else None
        )
        itd = {
            "absolute_pct": abs_ret["gain_pct"],
            "absolute_inr": abs_ret["gain_inr"] if value is not None else None,
            "xirr": xirr_v,
            "cagr": cagr_v,
            "benchmark_return": bench_ret,
            "absolute_excess_pp": absolute_excess,
            "xirr_excess_pp": xirr_excess,
            "cagr_excess_pp": cagr_excess,
        }
        rows.append(
            {
                "instrument_id": inst.id,
                "symbol": inst.symbol,
                "instrument_type": inst.instrument_type,
                "qty": qty,
                "avg_price": avg,
                "ltp": ltp,
                "value": value,
                "absolute_pct": itd["absolute_pct"],
                "absolute_inr": itd["absolute_inr"],
                "xirr": xirr_v,
                "cagr": cagr_v,
                "benchmark": bmap.benchmark_index,
                "benchmark_return": bench_ret,
                "absolute_excess_pp": absolute_excess,
                "xirr_excess_pp": xirr_excess,
                "cagr_excess_pp": cagr_excess,
                "incomplete": ltp is None or bench_ret is None,
                "needs_category": bool(inst.needs_category),
                "windows": {"ITD": itd, "1Y": None, "3Y": None, "5Y": None},
                "_bench_cagr": bench_cagr,  # stripped in API responses if desired; used by overview
            }
        )
    return rows


def get_overview(session: Session, as_of: str) -> dict:
    holdings = get_holdings(session, as_of)
    total_value = sum(h["value"] or 0.0 for h in holdings)
    all_txs = session.query(Transaction).order_by(Transaction.trade_date.asc()).all()
    by_inst: dict[int, list] = {}
    for t in all_txs:
        by_inst.setdefault(t.instrument_id, []).append(t)
    invested = 0.0
    for txs in by_inst.values():
        invested += metrics.invested_cost_from_transactions(
            [(t.side, t.quantity, t.price, t.fees) for t in txs]
        )
    abs_ret = metrics.absolute_return(invested, total_value)
    flows = metrics.build_xirr_cashflows(
        [(t.trade_date, t.side, t.quantity, t.price, t.fees) for t in all_txs],
        total_value,
        as_of,
    )
    first_date = all_txs[0].trade_date if all_txs else as_of
    weights_returns: list[tuple[float, float]] = []
    weights_cagr: list[tuple[float, float]] = []
    # Portfolio bench XIRR: same cashflows, terminal = sum of per-instrument index terminals
    index_terminal = 0.0
    index_terminal_ok = True
    for h in holdings:
        if h["value"] and total_value > 0 and h["benchmark_return"] is not None:
            w = h["value"] / total_value
            weights_returns.append((w, h["benchmark_return"]))
            if h.get("_bench_cagr") is not None:
                weights_cagr.append((w, h["_bench_cagr"]))
        inst = session.get(Instrument, h["instrument_id"])
        if inst is None:
            continue
        bmap = benchmarks.ensure_benchmark_map(session, inst)
        txs = by_inst.get(h["instrument_id"], [])
        trade_tuples = [(t.trade_date, t.side, t.quantity, t.price, t.fees) for t in txs]
        term = metrics.index_units_terminal_mv(
            trade_tuples, _index_price_fn(session, bmap.benchmark_index), as_of
        )
        if term is None:
            index_terminal_ok = False
        else:
            index_terminal += term
    blended = benchmarks.portfolio_blended_benchmark_return(weights_returns)
    blended_cagr = (
        benchmarks.portfolio_blended_benchmark_return(weights_cagr) if weights_cagr else None
    )
    xirr_v = metrics.xirr(flows)
    cagr_v = metrics.cagr(invested, total_value, first_date, as_of) if invested > 0 else None
    bench_xirr = None
    if index_terminal_ok and all_txs:
        bench_flows = metrics.build_xirr_cashflows(
            [(t.trade_date, t.side, t.quantity, t.price, t.fees) for t in all_txs],
            index_terminal,
            as_of,
        )
        bench_xirr = metrics.xirr(bench_flows)
    absolute_excess = (
        metrics.excess_pp(abs_ret["gain_pct"], blended)
        if abs_ret["gain_pct"] is not None and weights_returns
        else None
    )
    xirr_excess = (
        metrics.excess_pp(xirr_v, bench_xirr)
        if xirr_v is not None and bench_xirr is not None
        else None
    )
    cagr_excess = (
        metrics.excess_pp(cagr_v, blended_cagr)
        if cagr_v is not None and blended_cagr is not None
        else None
    )
    itd_bundle = {
        "absolute_pct": abs_ret["gain_pct"],
        "absolute_inr": abs_ret["gain_inr"],
        "xirr": xirr_v,
        "cagr": cagr_v,
        "benchmark_return": blended if weights_returns else None,
        "absolute_excess_pp": absolute_excess,
        "xirr_excess_pp": xirr_excess,
        "cagr_excess_pp": cagr_excess,
    }
    allocation = [
        {
            "symbol": h["symbol"],
            "weight": (h["value"] / total_value) if h["value"] and total_value else 0.0,
        }
        for h in holdings
    ]
    # Strip internal fields from holdings-shaped payloads when returning overview-only
    return {
        "as_of": as_of,
        "total_value": total_value,
        "absolute": abs_ret,
        "xirr": xirr_v,
        "cagr": cagr_v,
        "benchmark_return": blended if weights_returns else None,
        "absolute_excess_pp": absolute_excess,
        "xirr_excess_pp": xirr_excess,
        "cagr_excess_pp": cagr_excess,
        "allocation": allocation,
        "incomplete": any(h["incomplete"] for h in holdings),
        "windows": {"ITD": itd_bundle, "1Y": None, "3Y": None, "5Y": None},
    }


def get_performance(session: Session, as_of: str) -> dict:
    # Filled in Task 8c — stub so imports resolve
    overview = get_overview(session, as_of)
    return {
        "overview": overview,
        "contributors": [],
        "holdings": get_holdings(session, as_of),
        "windows_available": [w for w, v in overview["windows"].items() if v is not None],
        "default_window": "ITD",
    }
```

Router:

```python
# apps/api/src/portfolio_tracker/routers/portfolio.py
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from portfolio_tracker.db.session import get_db
from portfolio_tracker.modules import portfolio

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/overview")
def overview(session: Session = Depends(get_db)) -> dict:
    return portfolio.get_overview(session, as_of=date.today().isoformat())


@router.get("/holdings")
def holdings(session: Session = Depends(get_db)) -> dict:
    rows = portfolio.get_holdings(session, as_of=date.today().isoformat())
    for r in rows:
        r.pop("_bench_cagr", None)
    return {"holdings": rows}


@router.get("/performance")
def performance(session: Session = Depends(get_db)) -> dict:
    return portfolio.get_performance(session, as_of=date.today().isoformat())
```

Include portfolio router in `create_app()`.

- [ ] **Step 4: Run tests**

Run: `cd apps/api && uv run pytest tests/test_portfolio.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/portfolio_tracker/modules/portfolio.py apps/api/src/portfolio_tracker/routers/portfolio.py apps/api/tests/test_portfolio.py apps/api/src/portfolio_tracker/main.py
git commit -m "feat: assemble ITD portfolio holdings and overview metrics"
```

---

### Task 8b: Rolling windows (1Y/3Y/5Y) on holdings + overview

**Files:**
- Modify: `apps/api/src/portfolio_tracker/modules/portfolio.py`
- Modify: `apps/api/tests/test_portfolio.py`

**Interfaces:**
- Consumes: Task 7 window helpers + Task 8a
- Produces:
  - `_build_instrument_windows(...)` / `_build_portfolio_windows(...)`
  - `HoldingRow.windows` and `Overview.windows` fully populated: `{ITD, 1Y, 3Y, 5Y}` with `null` when insufficient history
  - Rolling MV at `window_start` from txs + prices (not holdings snapshot)
  - Rolling XIRR excess via `benchmark_xirr_from_trades(..., opening_mv=..., window_start=...)`
  - Trades in window: `start < trade_date <= as_of` (position on `start` already in opening MV)

- [ ] **Step 1: Extend seed + failing rolling tests**

```python
# append to apps/api/tests/test_portfolio.py

def _seed_with_window_prices(session):
    inst = _seed_itd(session)
    # 1Y window for as_of 2024-06-01 starts 2023-06-02 — need marks near start
    session.add(Price(symbol="RELIANCE.NS", price_date="2023-06-02", close=2200.0, source="yahoo"))
    session.add(BenchmarkPrice(index_symbol="Nifty 500", price_date="2023-06-02", close=11000.0))
    session.commit()
    return inst


def test_overview_rolling_1y_available_3y_5y_null():
    Session = get_session_factory()
    with Session() as session:
        _seed_with_window_prices(session)
        overview = portfolio.get_overview(session, as_of="2024-06-01")
        assert overview["windows"]["1Y"] is not None
        assert overview["windows"]["1Y"]["absolute_pct"] is not None
        assert overview["windows"]["1Y"]["xirr"] is not None
        assert overview["windows"]["1Y"]["xirr_excess_pp"] is not None
        assert overview["windows"]["3Y"] is None
        assert overview["windows"]["5Y"] is None


def test_holdings_include_windows():
    Session = get_session_factory()
    with Session() as session:
        _seed_with_window_prices(session)
        rows = portfolio.get_holdings(session, as_of="2024-06-01")
        assert "windows" in rows[0]
        assert rows[0]["windows"]["ITD"] is not None
        assert rows[0]["windows"]["1Y"] is not None
        assert rows[0]["windows"]["3Y"] is None
```

- [ ] **Step 2: Run to verify fail (1Y still null)**

Run: `cd apps/api && uv run pytest tests/test_portfolio.py::test_overview_rolling_1y_available_3y_5y_null tests/test_portfolio.py::test_holdings_include_windows -v`

Expected: FAIL on 1Y assertions

- [ ] **Step 3: Implement window builders; wire into `get_holdings` / `get_overview`**

```python
def _qty_at(txs: list[Transaction], as_of_day: str) -> float:
    qty = 0.0
    for t in txs:
        if t.trade_date > as_of_day:
            break
        qty += t.quantity if t.side == "buy" else -t.quantity
    return qty


def _build_instrument_windows(
    session: Session,
    inst: Instrument,
    txs: list[Transaction],
    first_date: str,
    as_of: str,
    itd_row: dict,
) -> dict:
    itd = {
        "absolute_pct": itd_row.get("absolute_pct"),
        "absolute_inr": itd_row.get("absolute_inr"),
        "xirr": itd_row.get("xirr"),
        "cagr": itd_row.get("cagr"),
        "benchmark_return": itd_row.get("benchmark_return"),
        "absolute_excess_pp": itd_row.get("absolute_excess_pp"),
        "xirr_excess_pp": itd_row.get("xirr_excess_pp"),
        "cagr_excess_pp": itd_row.get("cagr_excess_pp"),
    }
    out: dict = {"ITD": itd}
    px_symbol = _instrument_price_symbol(inst)
    terminal = itd_row.get("value") or 0.0
    bmap = benchmarks.ensure_benchmark_map(session, inst)
    idx_fn = _index_price_fn(session, bmap.benchmark_index)
    for window in ("1Y", "3Y", "5Y"):
        start = metrics.window_start(as_of, window, first_date)
        if start is None:
            out[window] = None
            continue
        qty0 = _qty_at(txs, start)
        px0 = _latest_price(session, px_symbol, start)
        opening_mv = (qty0 * px0) if qty0 > 0 and px0 is not None else 0.0
        in_window = [t for t in txs if start < t.trade_date <= as_of]
        trade_tuples = [(t.trade_date, t.side, t.quantity, t.price, t.fees) for t in in_window]
        flows = metrics.build_rolling_xirr_cashflows(
            opening_mv=opening_mv,
            window_start=start,
            trades_in_window=trade_tuples,
            terminal_mv=terminal,
            as_of=as_of,
        )
        abs_pct = metrics.point_to_point_return(opening_mv, terminal)
        if abs_pct is None:
            w_invested = metrics.invested_cost_from_transactions(
                [(t.side, t.quantity, t.price, t.fees) for t in in_window]
            )
            abs_bundle = metrics.absolute_return(w_invested, terminal)
            abs_pct = abs_bundle["gain_pct"]
            abs_inr = abs_bundle["gain_inr"]
        else:
            abs_inr = terminal - opening_mv
        xirr_v = metrics.xirr(flows)
        cagr_v = metrics.cagr(opening_mv, terminal, start, as_of) if opening_mv > 0 else None
        b0 = _price_on_or_after(session, bmap.benchmark_index, start)
        b1 = _benchmark_price(session, bmap.benchmark_index, as_of)
        bench_ret = metrics.benchmark_return(b0, b1) if b0 and b1 else None
        bench_cagr = metrics.cagr(b0, b1, start, as_of) if b0 and b1 else None
        bench_xirr = metrics.benchmark_xirr_from_trades(
            trade_tuples,
            idx_fn,
            as_of,
            opening_mv=opening_mv,
            window_start=start,
        )
        out[window] = {
            "absolute_pct": abs_pct,
            "absolute_inr": abs_inr,
            "xirr": xirr_v,
            "cagr": cagr_v,
            "benchmark_return": bench_ret,
            "absolute_excess_pp": (
                metrics.excess_pp(abs_pct, bench_ret)
                if abs_pct is not None and bench_ret is not None
                else None
            ),
            "xirr_excess_pp": (
                metrics.excess_pp(xirr_v, bench_xirr)
                if xirr_v is not None and bench_xirr is not None
                else None
            ),
            "cagr_excess_pp": (
                metrics.excess_pp(cagr_v, bench_cagr)
                if cagr_v is not None and bench_cagr is not None
                else None
            ),
        }
    return out


def _build_portfolio_windows(
    session: Session,
    *,
    all_txs: list[Transaction],
    first_date: str,
    as_of: str,
    total_value: float,
    itd_bundle: dict,
    holdings: list[dict],
) -> dict:
    by_inst: dict[int, list[Transaction]] = {}
    for t in all_txs:
        by_inst.setdefault(t.instrument_id, []).append(t)
    out: dict = {"ITD": itd_bundle}
    for window in ("1Y", "3Y", "5Y"):
        start = metrics.window_start(as_of, window, first_date)
        if start is None:
            out[window] = None
            continue
        opening_mv = 0.0
        weights_bench: list[tuple[float, float]] = []
        weights_cagr: list[tuple[float, float]] = []
        index_terminal = 0.0
        index_ok = True
        for iid, txs in by_inst.items():
            inst = session.get(Instrument, iid)
            if inst is None:
                continue
            qty = _qty_at(txs, start)
            px = _latest_price(session, _instrument_price_symbol(inst), start)
            value_start = (qty * px) if qty > 0 and px is not None else 0.0
            opening_mv += value_start
            bmap = benchmarks.ensure_benchmark_map(session, inst)
            b0 = _price_on_or_after(session, bmap.benchmark_index, start)
            b1 = _benchmark_price(session, bmap.benchmark_index, as_of)
            br = metrics.benchmark_return(b0, b1) if b0 and b1 else None
            bc = metrics.cagr(b0, b1, start, as_of) if b0 and b1 else None
            cur_px = _latest_price(session, _instrument_price_symbol(inst), as_of)
            cur_qty = _qty_at(txs, as_of)
            cur_val = (cur_px * cur_qty) if cur_px is not None else value_start
            if br is not None and cur_val > 0:
                weights_bench.append((cur_val, br))
            if bc is not None and cur_val > 0:
                weights_cagr.append((cur_val, bc))
            in_w = [t for t in txs if start < t.trade_date <= as_of]
            term = metrics.index_units_terminal_mv(
                [(t.trade_date, t.side, t.quantity, t.price, t.fees) for t in in_w],
                _index_price_fn(session, bmap.benchmark_index),
                as_of,
                opening_mv=value_start,
                window_start=start,
            )
            if term is None:
                index_ok = False
            else:
                index_terminal += term
        in_window = [t for t in all_txs if start < t.trade_date <= as_of]
        trade_tuples = [(t.trade_date, t.side, t.quantity, t.price, t.fees) for t in in_window]
        flows = metrics.build_rolling_xirr_cashflows(
            opening_mv=opening_mv,
            window_start=start,
            trades_in_window=trade_tuples,
            terminal_mv=total_value,
            as_of=as_of,
        )
        abs_pct = metrics.point_to_point_return(opening_mv, total_value)
        if abs_pct is None:
            w_invested = metrics.invested_cost_from_transactions(
                [(t.side, t.quantity, t.price, t.fees) for t in in_window]
            )
            abs_bundle = metrics.absolute_return(w_invested, total_value)
            abs_pct, abs_inr = abs_bundle["gain_pct"], abs_bundle["gain_inr"]
        else:
            abs_inr = total_value - opening_mv
        xirr_v = metrics.xirr(flows)
        cagr_v = metrics.cagr(opening_mv, total_value, start, as_of) if opening_mv > 0 else None
        total_w = sum(w for w, _ in weights_bench) or 0.0
        blended = (
            benchmarks.portfolio_blended_benchmark_return(
                [(w / total_w, r) for w, r in weights_bench]
            )
            if total_w > 0
            else None
        )
        total_cw = sum(w for w, _ in weights_cagr) or 0.0
        blended_cagr = (
            benchmarks.portfolio_blended_benchmark_return(
                [(w / total_cw, r) for w, r in weights_cagr]
            )
            if total_cw > 0
            else None
        )
        bench_xirr = None
        if index_ok:
            bflows = metrics.build_rolling_xirr_cashflows(
                opening_mv=opening_mv,
                window_start=start,
                trades_in_window=trade_tuples,
                terminal_mv=index_terminal,
                as_of=as_of,
            )
            bench_xirr = metrics.xirr(bflows)
        out[window] = {
            "absolute_pct": abs_pct,
            "absolute_inr": abs_inr,
            "xirr": xirr_v,
            "cagr": cagr_v,
            "benchmark_return": blended,
            "absolute_excess_pp": (
                metrics.excess_pp(abs_pct, blended)
                if abs_pct is not None and blended is not None
                else None
            ),
            "xirr_excess_pp": (
                metrics.excess_pp(xirr_v, bench_xirr)
                if xirr_v is not None and bench_xirr is not None
                else None
            ),
            "cagr_excess_pp": (
                metrics.excess_pp(cagr_v, blended_cagr)
                if cagr_v is not None and blended_cagr is not None
                else None
            ),
        }
    return out
```

In `get_holdings`, after building each ITD row, set  
`row["windows"] = _build_instrument_windows(session, inst, txs, first_date, as_of, row)`.

In `get_overview`, replace stub `windows` with  
`_build_portfolio_windows(..., holdings=holdings)`.

- [ ] **Step 4: Run tests**

Run: `cd apps/api && uv run pytest tests/test_portfolio.py tests/test_metrics.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/portfolio_tracker/modules/portfolio.py apps/api/tests/test_portfolio.py
git commit -m "feat: add trailing 1Y/3Y/5Y window metrics on holdings and overview"
```

---

### Task 8c: Performance endpoint + contributors

**Files:**
- Modify: `apps/api/src/portfolio_tracker/modules/portfolio.py`
- Modify: `apps/api/tests/test_portfolio.py`

**Interfaces:**
- Consumes: 8a/8b holdings + overview
- Produces: `get_performance(session, as_of) -> {overview, contributors, holdings, windows_available, default_window}`
  - Contributors sorted by absolute excess (desc); each includes `windows`
  - Holdings in response already include `windows` from 8b

- [ ] **Step 1: Failing performance test**

```python
def test_performance_has_contributors_and_windows():
    Session = get_session_factory()
    with Session() as session:
        _seed_with_window_prices(session)
        perf = portfolio.get_performance(session, as_of="2024-06-01")
        assert perf["default_window"] == "ITD"
        assert "1Y" in perf["windows_available"]
        assert len(perf["contributors"]) >= 1
        assert "windows" in perf["holdings"][0]
        assert perf["overview"]["windows"]["1Y"] is not None
```

- [ ] **Step 2: Run to verify fail**

Run: `cd apps/api && uv run pytest tests/test_portfolio.py::test_performance_has_contributors_and_windows -v`

Expected: FAIL (empty contributors stub)

- [ ] **Step 3: Implement `get_performance`**

```python
def get_performance(session: Session, as_of: str) -> dict:
    overview = get_overview(session, as_of)
    holdings = get_holdings(session, as_of)
    for r in holdings:
        r.pop("_bench_cagr", None)
    contributors = sorted(
        [
            {
                "symbol": h["symbol"],
                "absolute_excess_pp": h["absolute_excess_pp"],
                "xirr_excess_pp": h["xirr_excess_pp"],
                "cagr_excess_pp": h["cagr_excess_pp"],
                "value": h["value"],
                "weight": (h["value"] / overview["total_value"])
                if h["value"] and overview["total_value"]
                else 0.0,
                "windows": h["windows"],
            }
            for h in holdings
            if h["absolute_excess_pp"] is not None or h["xirr_excess_pp"] is not None
        ],
        key=lambda r: (r["absolute_excess_pp"] is not None, r["absolute_excess_pp"] or 0.0),
        reverse=True,
    )
    return {
        "overview": overview,
        "contributors": contributors,
        "holdings": holdings,
        "windows_available": [w for w, v in overview["windows"].items() if v is not None],
        "default_window": "ITD",
    }
```

- [ ] **Step 4: Run full portfolio + metrics tests**

Run: `cd apps/api && uv run pytest tests/test_portfolio.py tests/test_metrics.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/portfolio_tracker/modules/portfolio.py apps/api/tests/test_portfolio.py
git commit -m "feat: add performance contributors with per-window excess"
```

---

### Task 9: Kite sync (holdings + today’s trades)

**Files:**
- Create: `apps/api/src/portfolio_tracker/modules/kite_sync.py`
- Create: `apps/api/src/portfolio_tracker/routers/sync.py`
- Create: `apps/api/tests/test_kite_sync.py`
- Modify: `apps/api/src/portfolio_tracker/main.py`

**Interfaces:**
- Consumes: `kite_auth.authenticated_kite`, `Session`, prices/portfolio optionally
- Produces:
  - `sync_all(session) -> SyncResult` with `holdings_count`, `trades_appended`, `last_sync_at`
  - Upserts `HoldingsSnapshot` for equity + MF holdings from Kite
  - Appends today’s trades from `kite.orders()` / `kite.trades()` with source=`api` and dedupe keys; skip if token invalid → raise `KiteAuthError`
  - Updates `last_sync_at`, `last_trade_append_at` settings
  - `POST /sync` → SyncResult; on auth error 401 with reconnect message

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_kite_sync.py
from unittest.mock import MagicMock, patch

from portfolio_tracker.db.engine import get_session_factory
from portfolio_tracker.db.models import HoldingsSnapshot, Setting, Transaction
from portfolio_tracker.modules import kite_auth, kite_sync


def test_sync_upserts_holdings_and_appends_trades():
    Session = get_session_factory()
    with Session() as session:
        session.add(Setting(key=kite_auth.TOKEN_KEY, value="tok"))
        session.commit()
        kite = MagicMock()
        kite.holdings.return_value = [
            {
                "tradingsymbol": "RELIANCE",
                "isin": "INE002A01018",
                "exchange": "NSE",
                "quantity": 10,
                "average_price": 2000.0,
                "instrument_type": "EQ",
            }
        ]
        kite.mf_holdings.return_value = []
        kite.trades.return_value = [
            {
                "trade_id": "99",
                "order_id": "55",
                "tradingsymbol": "RELIANCE",
                "exchange": "NSE",
                "transaction_type": "BUY",
                "quantity": 1,
                "average_price": 2100.0,
                "fill_timestamp": "2026-08-01 10:00:00",
            }
        ]
        with patch.object(kite_auth, "authenticated_kite", return_value=kite):
            with patch.object(kite_sync, "_today_ist", return_value="2026-08-01"):
                result = kite_sync.sync_all(session)
        session.commit()
        assert result["holdings_count"] == 1
        assert result["trades_appended"] == 1
        assert session.query(HoldingsSnapshot).count() == 1
        assert session.query(Transaction).filter(Transaction.source == "api").count() == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && uv run pytest tests/test_kite_sync.py -v`

Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# apps/api/src/portfolio_tracker/modules/kite_sync.py
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from portfolio_tracker.db.models import HoldingsSnapshot, Instrument, Transaction
from portfolio_tracker.modules import kite_auth
from portfolio_tracker.modules.csv_import import get_or_create_instrument

IST = ZoneInfo("Asia/Kolkata")


def _today_ist() -> str:
    return datetime.now(IST).date().isoformat()


def _upsert_holding(session: Session, inst: Instrument, qty: float, avg: float, as_of: str) -> None:
    row = session.query(HoldingsSnapshot).filter(HoldingsSnapshot.instrument_id == inst.id).first()
    if row:
        row.quantity = qty
        row.avg_price = avg
        row.as_of = as_of
    else:
        session.add(HoldingsSnapshot(instrument_id=inst.id, quantity=qty, avg_price=avg, as_of=as_of))


def sync_all(session: Session) -> dict:
    kite = kite_auth.authenticated_kite(session)
    as_of = _today_ist()
    holdings_count = 0

    for h in kite.holdings() or []:
        symbol = h["tradingsymbol"]
        inst = get_or_create_instrument(
            session,
            symbol=symbol,
            isin=h.get("isin"),
            instrument_type="etf" if "ETF" in symbol.upper() else "equity",
            exchange=h.get("exchange"),
        )
        _upsert_holding(session, inst, float(h["quantity"]), float(h["average_price"]), as_of)
        holdings_count += 1

    for h in kite.mf_holdings() or []:
        symbol = h.get("tradingsymbol") or h.get("isin")
        inst = get_or_create_instrument(
            session,
            symbol=symbol,
            isin=h.get("isin"),
            instrument_type="mf",
            exchange=None,
        )
        qty = float(h.get("quantity") or 0)
        avg = float(h.get("average_price") or h.get("last_price") or 0)
        _upsert_holding(session, inst, qty, avg, as_of)
        holdings_count += 1

    appended = 0
    for t in kite.trades() or []:
        fill = (t.get("fill_timestamp") or "")[:10]
        if fill != as_of:
            continue
        symbol = t["tradingsymbol"]
        side = "buy" if str(t.get("transaction_type", "")).upper() == "BUY" else "sell"
        qty = float(t["quantity"])
        price = float(t.get("average_price") or t.get("price") or 0)
        order_id = str(t.get("trade_id") or t.get("order_id"))
        dedupe = f"api:{symbol}:{fill}:{side}:{qty}:{price}:{order_id}"
        if session.query(Transaction).filter(Transaction.dedupe_key == dedupe).first():
            continue
        inst = get_or_create_instrument(
            session,
            symbol=symbol,
            isin=t.get("isin"),
            instrument_type="equity",
            exchange=t.get("exchange"),
        )
        session.add(
            Transaction(
                instrument_id=inst.id,
                trade_date=fill,
                side=side,
                quantity=qty,
                price=price,
                fees=0.0,
                source="api",
                dedupe_key=dedupe,
                raw_order_id=order_id,
            )
        )
        appended += 1

    now = datetime.now(IST).isoformat()
    kite_auth.set_setting(session, kite_auth.LAST_SYNC_KEY, now)
    kite_auth.set_setting(session, kite_auth.LAST_APPEND_KEY, now)
    return {"holdings_count": holdings_count, "trades_appended": appended, "last_sync_at": now}
```

```python
# apps/api/src/portfolio_tracker/routers/sync.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from portfolio_tracker.db.session import get_db
from portfolio_tracker.modules import kite_auth, kite_sync
from portfolio_tracker.modules.prices import refresh_prices

router = APIRouter(tags=["sync"])


@router.post("/sync")
def sync(session: Session = Depends(get_db)) -> dict:
    if not kite_auth.is_token_valid(session):
        raise HTTPException(status_code=401, detail="Reconnect Zerodha — access token missing or expired")
    try:
        result = kite_sync.sync_all(session)
        prices = refresh_prices(session)
        result["prices"] = prices
        return result
    except kite_auth.KiteAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
```

Include sync router in `create_app()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/api && uv run pytest tests/test_kite_sync.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/portfolio_tracker/modules/kite_sync.py apps/api/src/portfolio_tracker/routers/sync.py apps/api/tests/test_kite_sync.py apps/api/src/portfolio_tracker/main.py apps/api/src/portfolio_tracker/modules/csv_import.py
git commit -m "feat: sync Kite holdings and append today's trades"
```

---

### Task 10: Reconcile + gap detection

**Files:**
- Create: `apps/api/src/portfolio_tracker/modules/reconcile.py`
- Create: `apps/api/tests/test_reconcile.py`
- Modify: `apps/api/src/portfolio_tracker/routers/portfolio.py` (or new `routers/reconcile.py`) — expose `GET /portfolio/alerts`

**Interfaces:**
- Consumes: `Transaction`, `HoldingsSnapshot`, settings `last_trade_append_at`
- Produces:
  - `transaction_implied_qty(session, instrument_id) -> float`
  - `reconcile_holdings(session) -> list[Diff]` (`symbol`, `holdings_qty`, `tx_qty`, `delta`)
  - `detect_gaps(session, today: str) -> GapWarning | None` — if `last_trade_append_at` date < previous calendar day by >1 day; returns `{"suggested_from", "suggested_to", "message"}` telling user which Console Tradebook date range to export (Equity and/or Mutual Funds)
  - Reconcile message: no manual txn fix — re-import Console CSV for the range and/or Sync now
  - Alerts payload used by Overview + Import banners

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_reconcile.py
from portfolio_tracker.db.engine import get_session_factory
from portfolio_tracker.db.models import HoldingsSnapshot, Instrument, Setting, Transaction
from portfolio_tracker.modules import kite_auth, reconcile


def test_reconcile_detects_qty_mismatch():
    Session = get_session_factory()
    with Session() as session:
        inst = Instrument(symbol="RELIANCE", instrument_type="equity", exchange="NSE")
        session.add(inst)
        session.flush()
        session.add(
            Transaction(
                instrument_id=inst.id,
                trade_date="2024-01-01",
                side="buy",
                quantity=5,
                price=100,
                fees=0,
                source="csv",
                dedupe_key="a",
            )
        )
        session.add(HoldingsSnapshot(instrument_id=inst.id, quantity=10, avg_price=100, as_of="2024-06-01"))
        session.commit()
        diffs = reconcile.reconcile_holdings(session)
        assert len(diffs) == 1
        assert diffs[0]["delta"] == 5


def test_gap_when_last_append_old():
    Session = get_session_factory()
    with Session() as session:
        session.add(Setting(key=kite_auth.LAST_APPEND_KEY, value="2024-01-01T10:00:00+05:30"))
        session.commit()
        gap = reconcile.detect_gaps(session, today="2024-01-10")
        assert gap is not None
        assert gap["suggested_from"] == "2024-01-02"
        assert gap["suggested_to"] == "2024-01-10"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && uv run pytest tests/test_reconcile.py -v`

Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# apps/api/src/portfolio_tracker/modules/reconcile.py
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from portfolio_tracker.db.models import HoldingsSnapshot, Instrument, Transaction
from portfolio_tracker.modules import kite_auth


def transaction_implied_qty(session: Session, instrument_id: int) -> float:
    qty = 0.0
    txs = (
        session.query(Transaction)
        .filter(Transaction.instrument_id == instrument_id)
        .order_by(Transaction.trade_date.asc())
        .all()
    )
    for t in txs:
        qty += t.quantity if t.side == "buy" else -t.quantity
    return qty


def reconcile_holdings(session: Session) -> list[dict]:
    diffs: list[dict] = []
    snaps = session.query(HoldingsSnapshot).all()
    for snap in snaps:
        inst = session.get(Instrument, snap.instrument_id)
        tx_qty = transaction_implied_qty(session, snap.instrument_id)
        delta = snap.quantity - tx_qty
        if abs(delta) > 1e-6:
            diffs.append(
                {
                    "instrument_id": snap.instrument_id,
                    "symbol": inst.symbol if inst else str(snap.instrument_id),
                    "holdings_qty": snap.quantity,
                    "tx_qty": tx_qty,
                    "delta": delta,
                }
            )
    return diffs


def detect_gaps(session: Session, today: str) -> dict | None:
    raw = kite_auth.get_setting(session, kite_auth.LAST_APPEND_KEY)
    if not raw:
        return None
    last_day = raw[:10]
    today_d = date.fromisoformat(today)
    last_d = date.fromisoformat(last_day)
    if today_d - last_d <= timedelta(days=1):
        return None
    suggested_from = (last_d + timedelta(days=1)).isoformat()
    return {
        "suggested_from": suggested_from,
        "suggested_to": today,
        "message": (
            f"Possible missing trades between {suggested_from} and {today}. "
            "In Console → Reports → Tradebook, export Equity and/or Mutual Funds "
            f"for {suggested_from} → {today} (max 365 days per file) and import here. "
            "Transactions are CSV/API only — no manual edits."
        ),
    }


def get_alerts(session: Session, today: str) -> dict:
    return {
        "token_connected": kite_auth.is_token_valid(session),
        "credentials_configured": kite_auth.get_auth_status(session)["credentials_configured"],
        "reconcile": reconcile_holdings(session),
        "gap": detect_gaps(session, today),
    }
```

Add route:

```python
@router.get("/alerts")
def alerts(session: Session = Depends(get_db)) -> dict:
    from datetime import date
    from portfolio_tracker.modules import reconcile
    return reconcile.get_alerts(session, today=date.today().isoformat())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/api && uv run pytest tests/test_reconcile.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/portfolio_tracker/modules/reconcile.py apps/api/tests/test_reconcile.py apps/api/src/portfolio_tracker/routers/portfolio.py
git commit -m "feat: add gap detection and holdings-vs-transactions reconcile"
```

---

### Task 11: API integration test + settings router

**Files:**
- Create: `apps/api/src/portfolio_tracker/routers/settings.py`
- Create: `apps/api/tests/test_api_integration.py`
- Modify: `apps/api/src/portfolio_tracker/main.py`
- Modify: `.gitignore` if needed

**Interfaces:**
- Consumes: all prior modules
- Produces:
  - `GET /settings/benchmarks` → list of instrument maps
  - `PUT /settings/benchmarks/{instrument_id}` body `{benchmark_index}` 
  - `PUT /settings/categories/{instrument_id}` body `{category}`
  - Integration test: import fixture CSV → seed prices/benchmarks → overview 200 with metrics (mocked Kite unused)

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_api_integration.py
from pathlib import Path

from fastapi.testclient import TestClient

from portfolio_tracker.db.engine import get_session_factory
from portfolio_tracker.db.models import BenchmarkPrice, Price
from portfolio_tracker.main import create_app

FIXTURES = Path(__file__).parent / "fixtures"


def test_import_then_overview(monkeypatch):
    client = TestClient(create_app())
    csv_text = (FIXTURES / "equity_tradebook.csv").read_text()
    response = client.post(
        "/import/csv",
        files={"file": ("equity.csv", csv_text, "text/csv")},
    )
    assert response.status_code == 200
    assert response.json()["new"] == 2

    Session = get_session_factory()
    with Session() as session:
        session.add(Price(symbol="RELIANCE.NS", price_date="2024-01-15", close=2500.0, source="yahoo"))
        session.add(Price(symbol="RELIANCE.NS", price_date="2026-08-01", close=3000.0, source="yahoo"))
        session.add(Price(symbol="INFY.NS", price_date="2024-02-01", close=1500.0, source="yahoo"))
        session.add(Price(symbol="INFY.NS", price_date="2026-08-01", close=1800.0, source="yahoo"))
        for idx in ("Nifty 500",):
            session.add(BenchmarkPrice(index_symbol=idx, price_date="2024-01-15", close=10000))
            session.add(BenchmarkPrice(index_symbol=idx, price_date="2026-08-01", close=12000))
        session.commit()

    overview = client.get("/portfolio/overview")
    assert overview.status_code == 200
    body = overview.json()
    assert body["total_value"] > 0
    alerts = client.get("/portfolio/alerts")
    assert alerts.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && uv run pytest tests/test_api_integration.py -v`

Expected: may FAIL on missing settings routes or overview wiring — fix until green in Step 3

- [ ] **Step 3: Write settings router + ensure all routers mounted**

```python
# apps/api/src/portfolio_tracker/routers/settings.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from portfolio_tracker.db.models import BenchmarkMap, Instrument
from portfolio_tracker.db.session import get_db
from portfolio_tracker.modules import benchmarks

router = APIRouter(prefix="/settings", tags=["settings"])


class BenchmarkBody(BaseModel):
    benchmark_index: str


class CategoryBody(BaseModel):
    category: str


@router.get("/benchmarks")
def list_benchmarks(session: Session = Depends(get_db)) -> dict:
    items = []
    for inst in session.query(Instrument).all():
        row = benchmarks.ensure_benchmark_map(session, inst)
        items.append(
            {
                "instrument_id": inst.id,
                "symbol": inst.symbol,
                "instrument_type": inst.instrument_type,
                "mf_category": inst.mf_category,
                "needs_category": bool(inst.needs_category),
                "benchmark_index": row.benchmark_index,
                "source": row.source,
            }
        )
    return {"items": items}


@router.put("/benchmarks/{instrument_id}")
def put_benchmark(instrument_id: int, body: BenchmarkBody, session: Session = Depends(get_db)) -> dict:
    if session.get(Instrument, instrument_id) is None:
        raise HTTPException(status_code=404, detail="Instrument not found")
    row = benchmarks.set_benchmark_override(session, instrument_id, body.benchmark_index)
    return {"instrument_id": instrument_id, "benchmark_index": row.benchmark_index, "source": row.source}


@router.put("/categories/{instrument_id}")
def put_category(instrument_id: int, body: CategoryBody, session: Session = Depends(get_db)) -> dict:
    try:
        inst = benchmarks.set_category_override(session, instrument_id, body.category)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"instrument_id": inst.id, "mf_category": inst.mf_category}
```

Confirm `create_app()` includes: `health`, `auth`, `import_`, `portfolio`, `sync`, `settings`.

- [ ] **Step 4: Run full API suite**

Run: `cd apps/api && uv run pytest -v`

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api
git commit -m "feat: add settings API and end-to-end import-to-overview test"
```

---

### Task 12: Next.js web scaffold + API client

**Files:**
- Create: `apps/web/*` (Next.js app)
- Create: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/lib/types.ts`
- Create: `apps/web/src/lib/format.ts`
- Create: `apps/web/src/components/Nav.tsx`
- Create: `apps/web/src/app/layout.tsx`
- Create: `apps/web/src/app/globals.css`
- Create: `apps/web/src/app/page.tsx` (placeholder Overview)
- Create: `apps/web/vitest.config.ts`
- Create: `apps/web/src/__tests__/format.test.ts`
- Modify: root `package.json` if needed

**Interfaces:**
- Consumes: API base URL `NEXT_PUBLIC_API_URL` default `http://127.0.0.1:8000`
- Produces: typed client functions `getOverview`, `getHoldings`, `getPerformance`, `getAlerts`, `getAuthStatus`, `getLoginUrl`, `postCallback`, `postSync`, `postImportCsv`, `getBenchmarkSettings`, `putBenchmark`, `putCategory`

- [ ] **Step 1: Scaffold Next.js app**

Run:

```bash
cd apps && npx --yes create-next-app@15 web --typescript --eslint --app --src-dir --no-tailwind --import-alias "@/*" --use-npm --turbopack false
```

If interactive prompts appear, pass flags to avoid them. Then add vitest:

```bash
cd apps/web && npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom @vitejs/plugin-react
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

- [ ] **Step 3: Implement format + api client + shell UI**

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
// apps/web/src/lib/types.ts
export type WindowKey = "ITD" | "1Y" | "3Y" | "5Y";

export type WindowMetrics = {
  absolute_pct: number | null;
  absolute_inr?: number | null;
  xirr: number | null;
  cagr: number | null;
  benchmark_return: number | null;
  absolute_excess_pp: number | null;
  xirr_excess_pp: number | null;
  cagr_excess_pp: number | null;
};

export type Overview = {
  as_of: string;
  total_value: number;
  absolute: { gain_inr: number; gain_pct: number | null; invested_cost: number; current_value: number };
  xirr: number | null;
  cagr: number | null;
  benchmark_return: number | null;
  absolute_excess_pp: number | null;
  xirr_excess_pp: number | null;
  cagr_excess_pp: number | null;
  allocation: { symbol: string; weight: number }[];
  incomplete: boolean;
  windows: Record<WindowKey, WindowMetrics | null>;
};

export type Holding = {
  instrument_id: number;
  symbol: string;
  instrument_type: string;
  qty: number;
  avg_price: number;
  ltp: number | null;
  value: number | null;
  absolute_pct: number | null;
  absolute_inr: number | null;
  xirr: number | null;
  cagr: number | null;
  benchmark: string;
  benchmark_return: number | null;
  absolute_excess_pp: number | null;
  xirr_excess_pp: number | null;
  cagr_excess_pp: number | null;
  incomplete: boolean;
  needs_category: boolean;
  windows: Record<WindowKey, WindowMetrics | null>;
};

export type Performance = {
  overview: Overview;
  contributors: {
    symbol: string;
    absolute_excess_pp: number | null;
    xirr_excess_pp: number | null;
    cagr_excess_pp: number | null;
    value: number | null;
    weight: number;
    windows: Record<WindowKey, WindowMetrics | null>;
  }[];
  holdings: Holding[];
  windows_available: WindowKey[];
  default_window: WindowKey;
};

export type Alerts = {
  token_connected: boolean;
  credentials_configured: boolean;
  reconcile: { symbol: string; holdings_qty: number; tx_qty: number; delta: number }[];
  gap: { suggested_from: string; suggested_to: string; message: string } | null;
};
```

```typescript
// apps/web/src/lib/api.ts
import type { Alerts, Holding, Overview, Performance } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { ...init, cache: "no-store" });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || res.statusText);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getOverview: () => request<Overview>("/portfolio/overview"),
  getHoldings: async () => {
    const data = await request<{ holdings: Holding[] }>("/portfolio/holdings");
    return data.holdings;
  },
  getPerformance: () => request<Performance>("/portfolio/performance"),
  getAlerts: () => request<Alerts>("/portfolio/alerts"),
  getAuthStatus: () =>
    request<{ connected: boolean; credentials_configured: boolean; last_sync_at: string | null }>(
      "/auth/status",
    ),
  getLoginUrl: () => request<{ login_url: string }>("/auth/login-url"),
  postCallback: (request_token: string) =>
    request<{ connected: boolean }>("/auth/callback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ request_token }),
    }),
  postSync: () => request<Record<string, unknown>>("/sync", { method: "POST" }),
  postImportCsv: async (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<{
      format: string;
      new: number;
      existing: number;
      segment_counts: Record<string, number>;
      flagged_rows: string[];
      date_min: string | null;
      date_max: string | null;
    }>("/import/csv", {
      method: "POST",
      body,
    });
  },
  getBenchmarkSettings: () => request<{ items: Record<string, unknown>[] }>("/settings/benchmarks"),
  putBenchmark: (instrumentId: number, benchmark_index: string) =>
    request(`/settings/benchmarks/${instrumentId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ benchmark_index }),
    }),
  putCategory: (instrumentId: number, category: string) =>
    request(`/settings/categories/${instrumentId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category }),
    }),
};
```

Nav links: Overview `/`, Holdings `/holdings`, Performance `/performance`, Import `/import`, Settings `/settings`.

Use a calm local-tool visual direction: deep forest green (`#1B4332`) on warm paper (`#F7F3EB`) with ink (`#1A1A1A`) — not purple, not cream-serif cliché overload; use `Source Serif 4` + `IBM Plex Sans` from Google Fonts for typography with purpose.

`vitest.config.ts`:

```typescript
import { defineConfig } from "vitest/config";
import path from "path";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: { environment: "jsdom", globals: true },
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
});
```

Add `"test": "vitest run"` to `apps/web/package.json` scripts.

- [ ] **Step 4: Run test**

Run: `cd apps/web && npm test`

Expected: PASS for format tests

- [ ] **Step 5: Commit**

```bash
git add apps/web package.json
git commit -m "chore: scaffold Next.js web app with API client"
```

---

### Task 13: Shared UI components + empty/banner states

**Files:**
- Create: `apps/web/src/components/MetricCard.tsx`
- Create: `apps/web/src/components/Banner.tsx`
- Create: `apps/web/src/components/EmptyState.tsx`
- Create: `apps/web/src/components/HoldingsTable.tsx`
- Create: `apps/web/src/__tests__/MetricCard.test.tsx`
- Create: `apps/web/src/__tests__/Banner.test.tsx`
- Create: `apps/web/src/__tests__/EmptyState.test.tsx`
- Create: `apps/web/src/__tests__/HoldingsTable.test.tsx`

**Interfaces:**
- Consumes: format helpers, Holding type
- Produces: presentational components used by pages

- [ ] **Step 1: Write failing component tests**

```tsx
// apps/web/src/__tests__/MetricCard.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MetricCard } from "@/components/MetricCard";

describe("MetricCard", () => {
  it("renders label and value", () => {
    render(<MetricCard label="XIRR" value="12.50%" hint="Inception-to-date" />);
    expect(screen.getByText("XIRR")).toBeTruthy();
    expect(screen.getByText("12.50%")).toBeTruthy();
  });
});
```

```tsx
// apps/web/src/__tests__/Banner.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Banner } from "@/components/Banner";

describe("Banner", () => {
  it("renders warning message", () => {
    render(<Banner tone="warning" title="Gap detected" body="Import CSV for missing days." />);
    expect(screen.getByText("Gap detected")).toBeTruthy();
  });
});
```

```tsx
// apps/web/src/__tests__/EmptyState.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EmptyState } from "@/components/EmptyState";

describe("EmptyState", () => {
  it("shows connect import sync CTA copy", () => {
    render(<EmptyState />);
    expect(screen.getByText(/Connect/i)).toBeTruthy();
    expect(screen.getByText(/Import/i)).toBeTruthy();
    expect(screen.getByText(/Sync/i)).toBeTruthy();
  });
});
```

```tsx
// apps/web/src/__tests__/HoldingsTable.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HoldingsTable } from "@/components/HoldingsTable";
import type { Holding } from "@/lib/types";

const sample: Holding = {
  instrument_id: 1,
  symbol: "RELIANCE",
  instrument_type: "equity",
  qty: 10,
  avg_price: 2000,
  ltp: 2600,
  value: 26000,
  absolute_pct: 0.3,
  absolute_inr: 6000,
  xirr: 0.12,
  cagr: 0.1,
  benchmark: "Nifty 500",
  benchmark_return: 0.2,
  absolute_excess_pp: 10,
  xirr_excess_pp: 8,
  cagr_excess_pp: 7,
  incomplete: false,
  needs_category: false,
  windows: { ITD: null, "1Y": null, "3Y": null, "5Y": null },
};

describe("HoldingsTable", () => {
  it("renders symbol and absolute excess", () => {
    render(<HoldingsTable rows={[sample]} />);
    expect(screen.getByText("RELIANCE")).toBeTruthy();
    expect(screen.getByText(/\+10\.00 pp/)).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/web && npm test`

Expected: FAIL missing components

- [ ] **Step 3: Implement components**

```tsx
// apps/web/src/components/MetricCard.tsx
export function MetricCard(props: { label: string; value: string; hint?: string }) {
  return (
    <div className="metric-card">
      <div className="metric-label">{props.label}</div>
      <div className="metric-value">{props.value}</div>
      {props.hint ? <div className="metric-hint">{props.hint}</div> : null}
    </div>
  );
}
```

```tsx
// apps/web/src/components/Banner.tsx
export function Banner(props: {
  tone: "warning" | "danger" | "info";
  title: string;
  body: string;
}) {
  return (
    <div className={`banner banner-${props.tone}`} role="status">
      <strong>{props.title}</strong>
      <p>{props.body}</p>
    </div>
  );
}
```

```tsx
// apps/web/src/components/EmptyState.tsx
import Link from "next/link";

export function EmptyState() {
  return (
    <section className="empty-state">
      <h2>Start tracking</h2>
      <ol>
        <li>
          <Link href="/settings">Connect</Link> Zerodha via Kite OAuth
        </li>
        <li>
          <Link href="/import">Import</Link> Console equity and/or Coin CSV
        </li>
        <li>
          <Link href="/settings">Sync</Link> holdings and refresh prices
        </li>
      </ol>
    </section>
  );
}
```

```tsx
// apps/web/src/components/HoldingsTable.tsx
import type { Holding } from "@/lib/types";
import { formatInr, formatPct, formatPp } from "@/lib/format";

export function HoldingsTable(props: { rows: Holding[] }) {
  return (
    <table className="holdings-table">
      <thead>
        <tr>
          <th>Symbol</th>
          <th>Qty</th>
          <th>Avg</th>
          <th>LTP</th>
          <th>Value</th>
          <th>Abs %</th>
          <th>XIRR</th>
          <th>CAGR</th>
          <th>Abs excess</th>
          <th>XIRR excess</th>
        </tr>
      </thead>
      <tbody>
        {props.rows.map((r) => (
          <tr key={r.instrument_id}>
            <td>
              {r.symbol}
              {r.needs_category ? " · set category" : ""}
              {r.incomplete ? " · incomplete" : ""}
            </td>
            <td>{r.qty}</td>
            <td>{formatInr(r.avg_price)}</td>
            <td>{formatInr(r.ltp)}</td>
            <td>{formatInr(r.value)}</td>
            <td>{formatPct(r.absolute_pct)}</td>
            <td>{formatPct(r.xirr)}</td>
            <td>{formatPct(r.cagr)}</td>
            <td>{formatPp(r.absolute_excess_pp)}</td>
            <td>{formatPp(r.xirr_excess_pp)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

Add CSS for these classes in `globals.css`.

- [ ] **Step 4: Run tests**

Run: `cd apps/web && npm test`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/components apps/web/src/__tests__ apps/web/src/app/globals.css
git commit -m "feat: add metric cards, banners, empty state, holdings table"
```

---

### Task 14: Settings + Import pages

**Files:**
- Create: `apps/web/src/app/settings/page.tsx`
- Create: `apps/web/src/app/import/page.tsx`
- Create: `apps/web/src/app/auth/callback/page.tsx` (reads `request_token` query, posts to API)

**Interfaces:**
- Consumes: `api.*`
- Produces: working Connect / Sync / Import / benchmark override UI

- [ ] **Step 1: Implement Settings page (client component)**

Settings must:
1. Show credentials_configured from `/auth/status` (never display secrets)
2. Connect button → fetch login URL → `window.location.href = login_url`
3. Sync now button → `POST /sync`; disable if not connected
4. List benchmark settings; allow changing benchmark index + MF category

```tsx
// apps/web/src/app/settings/page.tsx
"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Banner } from "@/components/Banner";

export default function SettingsPage() {
  const [status, setStatus] = useState<{
    connected: boolean;
    credentials_configured: boolean;
    last_sync_at: string | null;
  } | null>(null);
  const [items, setItems] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    const [s, b] = await Promise.all([api.getAuthStatus(), api.getBenchmarkSettings()]);
    setStatus(s);
    setItems(b.items);
  }

  useEffect(() => {
    refresh().catch((e) => setError(String(e)));
  }, []);

  async function connect() {
    const { login_url } = await api.getLoginUrl();
    window.location.href = login_url;
  }

  async function syncNow() {
    setBusy(true);
    setError(null);
    try {
      await api.postSync();
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <h1>Settings</h1>
      {!status?.credentials_configured ? (
        <Banner
          tone="info"
          title="Add Kite credentials"
          body="Copy .env.example to .env and set KITE_API_KEY and KITE_API_SECRET, then restart the API."
        />
      ) : null}
      {status && !status.connected ? (
        <Banner tone="warning" title="Not connected" body="Connect Zerodha to enable sync." />
      ) : null}
      {error ? <Banner tone="danger" title="Error" body={error} /> : null}
      <div className="actions">
        <button type="button" onClick={connect} disabled={!status?.credentials_configured}>
          Connect Zerodha
        </button>
        <button type="button" onClick={syncNow} disabled={!status?.connected || busy}>
          Sync now
        </button>
      </div>
      <p>Last sync: {status?.last_sync_at ?? "—"}</p>
      <h2>Benchmarks</h2>
      <ul>
        {items.map((item) => (
          <li key={String(item.instrument_id)}>
            {String(item.symbol)} ({String(item.source)})
            <select
              value={String(item.benchmark_index)}
              onChange={(e) =>
                api.putBenchmark(Number(item.instrument_id), e.target.value).then(refresh)
              }
            >
              {[
                "Nifty 50",
                "Nifty 100",
                "Nifty 500",
                "Nifty Midcap 150",
                "Nifty Smallcap 250",
              ].map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </li>
        ))}
      </ul>
    </main>
  );
}
```

OAuth callback page (Kite redirects to API URL typically — if redirect is API, API should redirect to web; for v1 set `KITE_REDIRECT_URL` to `http://localhost:3000/auth/callback` and exchange from web):

Update `.env.example` redirect to web callback:

```
KITE_REDIRECT_URL=http://localhost:3000/auth/callback
```

```tsx
// apps/web/src/app/auth/callback/page.tsx
"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

export default function AuthCallbackPage() {
  const params = useSearchParams();
  const router = useRouter();
  const [msg, setMsg] = useState("Connecting…");

  useEffect(() => {
    const token = params.get("request_token");
    if (!token) {
      setMsg("Missing request_token");
      return;
    }
    api
      .postCallback(token)
      .then(() => {
        setMsg("Connected");
        router.replace("/settings");
      })
      .catch((e) => setMsg(String(e)));
  }, [params, router]);

  return <main>{msg}</main>;
}
```

- [ ] **Step 2: Implement Import page**

```tsx
// apps/web/src/app/import/page.tsx
"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Alerts } from "@/lib/types";
import { Banner } from "@/components/Banner";

export default function ImportPage() {
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [alerts, setAlerts] = useState<Alerts | null>(null);

  useEffect(() => {
    api.getAlerts().then(setAlerts).catch(() => undefined);
  }, []);

  async function onFile(file: File | null) {
    if (!file) return;
    setError(null);
    try {
      const res = await api.postImportCsv(file);
      const segs = Object.entries(res.segment_counts)
        .map(([k, v]) => `${k}=${v}`)
        .join(", ");
      const flagged =
        res.flagged_rows.length > 0
          ? ` Flagged: ${res.flagged_rows.slice(0, 5).join("; ")}`
          : "";
      setResult(
        `Imported ${res.format}: ${res.new} new, ${res.existing} existing (${segs}).` +
          ` Range ${res.date_min ?? "?"} → ${res.date_max ?? "?"}.${flagged}`,
      );
      setAlerts(await api.getAlerts());
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <main>
      <h1>Import</h1>
      <p>
        Upload Zerodha Console tradebook CSVs: Reports → Tradebook → Equity and/or Mutual Funds.
        Console allows at most 365 days per download — import multiple files for full history.
      </p>
      {alerts?.gap ? (
        <Banner tone="warning" title="Missing export range" body={alerts.gap.message} />
      ) : null}
      {alerts && alerts.reconcile.length > 0 ? (
        <Banner
          tone="danger"
          title="Holdings ≠ transactions"
          body={
            "Re-import the Console tradebook covering the mismatched symbols, then Sync. " +
            alerts.reconcile.map((d) => `${d.symbol}: Δ ${d.delta}`).join("; ")
          }
        />
      ) : null}
      <input
        type="file"
        accept=".csv,text/csv"
        onChange={(e) => onFile(e.target.files?.[0] ?? null)}
      />
      {result ? <Banner tone="info" title="Import complete" body={result} /> : null}
      {error ? <Banner tone="danger" title="Import failed" body={error} /> : null}
    </main>
  );
}
```

- [ ] **Step 3: Manual smoke (dev)**

Run API + web; open Import with fixture CSV; open Settings (credentials banner if empty env).

- [ ] **Step 4: Run web tests**

Run: `cd apps/web && npm test`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/web .env.example
git commit -m "feat: add Settings, OAuth callback, and CSV Import pages"
```

---

### Task 15: Overview, Holdings, Performance pages

**Files:**
- Modify: `apps/web/src/app/page.tsx`
- Create: `apps/web/src/app/holdings/page.tsx`
- Create: `apps/web/src/app/performance/page.tsx`
- Create: `apps/web/src/components/AllocationChart.tsx`
- Create: `apps/web/src/components/PerformanceChart.tsx`

**Interfaces:**
- Consumes: overview/holdings/performance/alerts APIs + components from Task 13
- Produces: full v1 dashboard pages with gap/reconcile/token banners

- [ ] **Step 1: Implement Overview**

```tsx
// apps/web/src/app/page.tsx
"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Alerts, Overview } from "@/lib/types";
import { MetricCard } from "@/components/MetricCard";
import { Banner } from "@/components/Banner";
import { EmptyState } from "@/components/EmptyState";
import { formatInr, formatPct, formatPp } from "@/lib/format";

export default function OverviewPage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [alerts, setAlerts] = useState<Alerts | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.getOverview(), api.getAlerts()])
      .then(([o, a]) => {
        setOverview(o);
        setAlerts(a);
      })
      .catch((e) => setError(String(e)));
  }, []);

  if (error) return <Banner tone="danger" title="Failed to load" body={error} />;
  if (!overview) return <main>Loading…</main>;
  if (overview.total_value === 0) return <EmptyState />;

  return (
    <main>
      <h1>Overview</h1>
      {alerts && !alerts.token_connected ? (
        <Banner tone="warning" title="Reconnect Zerodha" body="Access token missing or expired. Sync is blocked." />
      ) : null}
      {alerts?.gap ? (
        <Banner tone="warning" title="Trade history gap" body={alerts.gap.message} />
      ) : null}
      {alerts && alerts.reconcile.length > 0 ? (
        <Banner
          tone="danger"
          title="Holdings do not match transactions"
          body={alerts.reconcile.map((d) => `${d.symbol}: Δ ${d.delta}`).join("; ")}
        />
      ) : null}
      {overview.incomplete ? (
        <Banner tone="info" title="Metrics incomplete" body="Some prices or benchmarks failed to load." />
      ) : null}
      <section className="metric-grid">
        <MetricCard label="Total value" value={formatInr(overview.total_value)} />
        <MetricCard
          label="Absolute P&L"
          value={formatInr(overview.absolute.gain_inr)}
          hint={formatPct(overview.absolute.gain_pct)}
        />
        <MetricCard label="XIRR" value={formatPct(overview.xirr)} hint="Inception-to-date" />
        <MetricCard label="CAGR" value={formatPct(overview.cagr)} hint="N/A if span &lt; 365 days" />
        <MetricCard label="Abs excess vs blend" value={formatPp(overview.absolute_excess_pp)} />
        <MetricCard label="XIRR excess vs blend" value={formatPp(overview.xirr_excess_pp)} />
        <MetricCard label="CAGR excess vs blend" value={formatPp(overview.cagr_excess_pp)} />
      </section>
      <section className="rolling-summaries">
        <h2>Trailing windows</h2>
        <p className="hint">
          Rolling absolute is opening MV → terminal MV (price path), not cashflow-adjusted.
        </p>
        {(["1Y", "3Y", "5Y"] as const).map((key) => {
          const w = overview.windows[key];
          if (!w) return null;
          return (
            <p key={key}>
              {key}: XIRR {formatPct(w.xirr)} · Abs {formatPct(w.absolute_pct)} · Excess{" "}
              {formatPp(w.xirr_excess_pp)}
            </p>
          );
        })}
      </section>
      <AllocationChart allocation={overview.allocation} />
    </main>
  );
}
```

- [ ] **Step 2: Charts**

```tsx
// apps/web/src/components/AllocationChart.tsx
type Props = { allocation: { symbol: string; weight: number }[] };

export function AllocationChart({ allocation }: Props) {
  const max = Math.max(...allocation.map((a) => a.weight), 0.0001);
  return (
    <figure className="chart">
      <figcaption>Allocation</figcaption>
      <svg viewBox={`0 0 320 ${Math.max(allocation.length, 1) * 28}`} width="100%" role="img">
        {allocation.map((a, i) => {
          const w = (a.weight / max) * 200;
          const y = i * 28 + 4;
          return (
            <g key={a.symbol}>
              <text x={0} y={y + 12} fontSize="12">
                {a.symbol}
              </text>
              <rect x={90} y={y} width={w} height={16} fill="currentColor" opacity={0.75} />
              <text x={96 + w} y={y + 12} fontSize="11">
                {(a.weight * 100).toFixed(1)}%
              </text>
            </g>
          );
        })}
      </svg>
    </figure>
  );
}
```

```tsx
// apps/web/src/components/PerformanceChart.tsx
type Row = { symbol: string; value: number | null };

type Props = { rows: Row[]; title: string };

export function PerformanceChart({ rows, title }: Props) {
  const vals = rows.map((r) => r.value ?? 0);
  const max = Math.max(...vals.map(Math.abs), 0.0001);
  return (
    <figure className="chart">
      <figcaption>{title}</figcaption>
      <svg viewBox={`0 0 320 ${Math.max(rows.length, 1) * 28}`} width="100%" role="img">
        {rows.map((r, i) => {
          const v = r.value ?? 0;
          const w = (Math.abs(v) / max) * 100;
          const y = i * 28 + 4;
          const x = v >= 0 ? 160 : 160 - w;
          return (
            <g key={r.symbol}>
              <text x={0} y={y + 12} fontSize="12">
                {r.symbol}
              </text>
              <line x1={160} y1={y} x2={160} y2={y + 16} stroke="currentColor" opacity={0.3} />
              <rect x={x} y={y} width={w} height={16} fill="currentColor" opacity={0.75} />
            </g>
          );
        })}
      </svg>
    </figure>
  );
}
```

- [ ] **Step 3: Holdings page**

```tsx
// apps/web/src/app/holdings/page.tsx
"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Holding } from "@/lib/types";
import { Banner } from "@/components/Banner";
import { HoldingsTable } from "@/components/HoldingsTable";

export default function HoldingsPage() {
  const [rows, setRows] = useState<Holding[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getHoldings()
      .then(setRows)
      .catch((e) => setError(String(e)));
  }, []);

  if (error) return <Banner tone="danger" title="Failed to load" body={error} />;
  if (!rows) return <main>Loading…</main>;

  return (
    <main>
      <h1>Holdings</h1>
      <p className="hint">ITD metrics by default. Open Performance for 1Y/3Y/5Y windows.</p>
      <HoldingsTable rows={rows} />
    </main>
  );
}
```

- [ ] **Step 4: Performance page**

```tsx
// apps/web/src/app/performance/page.tsx
"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { Performance, WindowKey } from "@/lib/types";
import { Banner } from "@/components/Banner";
import { MetricCard } from "@/components/MetricCard";
import { PerformanceChart } from "@/components/PerformanceChart";
import { formatPct, formatPp } from "@/lib/format";

const ALL: WindowKey[] = ["ITD", "1Y", "3Y", "5Y"];

export default function PerformancePage() {
  const [data, setData] = useState<Performance | null>(null);
  const [windowKey, setWindowKey] = useState<WindowKey>("ITD");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getPerformance()
      .then((p) => {
        setData(p);
        setWindowKey(p.default_window);
      })
      .catch((e) => setError(String(e)));
  }, []);

  const metrics = data?.overview.windows[windowKey] ?? null;

  const chartRows = useMemo(() => {
    if (!data) return [];
    return data.contributors.map((c) => ({
      symbol: c.symbol,
      value: c.windows[windowKey]?.absolute_excess_pp ?? c.absolute_excess_pp,
    }));
  }, [data, windowKey]);

  if (error) return <Banner tone="danger" title="Failed to load" body={error} />;
  if (!data) return <main>Loading…</main>;

  return (
    <main>
      <h1>Performance</h1>
      <p className="hint">
        Rolling absolute uses opening MV → terminal MV (price path). XIRR excess vs same-cashflow
        benchmark XIRR.
      </p>
      <div className="window-switcher" role="group" aria-label="Return window">
        {ALL.map((key) => {
          const available = data.overview.windows[key] != null;
          return (
            <button
              key={key}
              type="button"
              disabled={!available}
              aria-pressed={windowKey === key}
              onClick={() => setWindowKey(key)}
            >
              {key}
            </button>
          );
        })}
      </div>
      {metrics ? (
        <section className="metric-grid">
          <MetricCard label="Absolute" value={formatPct(metrics.absolute_pct)} />
          <MetricCard label="XIRR" value={formatPct(metrics.xirr)} />
          <MetricCard label="CAGR" value={formatPct(metrics.cagr)} />
          <MetricCard label="Abs excess" value={formatPp(metrics.absolute_excess_pp)} />
          <MetricCard label="XIRR excess" value={formatPp(metrics.xirr_excess_pp)} />
          <MetricCard label="CAGR excess" value={formatPp(metrics.cagr_excess_pp)} />
        </section>
      ) : (
        <Banner tone="info" title="Window unavailable" body="Insufficient history for this window." />
      )}
      <PerformanceChart rows={chartRows} title={`Contributor absolute excess (${windowKey})`} />
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Weight</th>
            <th>Abs excess</th>
            <th>XIRR excess</th>
            <th>CAGR excess</th>
          </tr>
        </thead>
        <tbody>
          {data.contributors.map((c) => {
            const w = c.windows[windowKey];
            return (
              <tr key={c.symbol}>
                <td>{c.symbol}</td>
                <td>{(c.weight * 100).toFixed(1)}%</td>
                <td>{formatPp(w?.absolute_excess_pp ?? c.absolute_excess_pp)}</td>
                <td>{formatPp(w?.xirr_excess_pp ?? c.xirr_excess_pp)}</td>
                <td>{formatPp(w?.cagr_excess_pp ?? c.cagr_excess_pp)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </main>
  );
}
```

- [ ] **Step 5: Run web tests + typecheck**

Run: `cd apps/web && npm test && npx tsc --noEmit`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add apps/web
git commit -m "feat: add Overview, Holdings, and Performance pages"
```

---

### Task 16: README + final wiring polish

**Files:**
- Create: `README.md`
- Create: `apps/api/README.md` (short)
- Modify: `.env.example`, `.gitignore`, root `package.json` scripts
- Ensure `data/.gitkeep` is NOT present if `data/` fully ignored — document creating `data/` on first run in README

**Interfaces:**
- Consumes: all prior work
- Produces: clone → configure → run instructions matching success criteria

- [ ] **Step 1: Write README**

README sections (required):
1. What it is (local BYO-Zerodha tracker)
2. Prerequisites (Python 3.12+, Node 20+, uv, Kite Connect Personal app)
3. Setup: clone, `cp .env.example .env`, fill keys, `cd apps/api && uv sync --extra dev`, `cd apps/web && npm install`
4. Run: `npm run api` and `npm run web`
5. First-run flow: Connect → Import Console Equity + Mutual Funds tradebooks (multi-file OK; ≤365 days each) → Sync
6. Where data lives (`data/portfolio.db`)
7. Testing: `npm test` / `npm run api:test` / `npm run web:test`
8. Security: never commit `.env`; CI uses mocks only
9. Market data: Yahoo Finance + AMFI; index ticker table from Task 5 (Smallcap = `NIFTYSMLCAP250.NS`)
10. Gaps/reconcile: Import UI shows suggested Console export range; no manual txn entry
11. Out of scope: free custom date picker, metrics cache (v2); rolling = fixed 1Y/3Y/5Y only
12. Pointer to design spec

- [ ] **Step 2: Verify config defaults**

Ensure `database_url` resolves to workspace `data/portfolio.db` when API started from `apps/api` (use absolute path helper if relative paths are fragile):

```python
# in config.py — preferred default
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[3]  # portfolio-tracker/
database_url: str = f"sqlite:///{_ROOT / 'data' / 'portfolio.db'}"
```

Create `data/` directory in `init_db()` if missing.

- [ ] **Step 3: Run full test suites**

Run: `npm test` from repo root (api + web)

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add README.md apps/api/README.md .env.example apps/api/src/portfolio_tracker/config.py apps/api/src/portfolio_tracker/db/engine.py package.json
git commit -m "docs: add setup README and harden local database path"
```

---

## Self-Review

### Spec coverage

| Spec requirement | Task(s) |
| ---------------- | ------- |
| Next.js + FastAPI + SQLite monorepo | 1, 12 |
| Kite Personal OAuth + token storage | 3, 14 |
| Holdings sync + today’s trade append | 9 |
| Console equity + Console MF tradebook CSV, idempotent | 4, 14 |
| Absolute / CAGR (≥365d) / XIRR whenever possible | 7, 8a |
| Trailing 1Y/3Y/5Y windows + ITD | 7, 8b, 15 |
| Excess absolute / XIRR (same-cashflow bench XIRR) / CAGR, per window | 7, 8a–8c, 15 |
| Portfolio `cagr_excess_pp` via blended bench CAGRs | 8a, 8b |
| Holdings include `windows` | 8b, 11, 15 |
| Benchmark category defaults + overrides | 6, 11, 14 |
| Value-weighted portfolio excess | 6, 8a–8b |
| Yahoo (.NS→.BO) + AMFI prices, PriceProvider | 5 |
| Gap detection + reconcile → CSV/API fix path | 10, 14, 15 |
| Overview / Holdings / Performance / Import / Settings | 13–15 |
| `.env.example`, README, secrets never committed | 1, 16 |
| API unit + integration tests; web component tests | 1–11, 12–13 |
| Empty state CTA Connect → Import → Sync | 13, 15 |
| No dividends; no free custom date picker | Global |
| No metrics_cache in v1 | 2, 8a (design spec aligned) |
| Public `get_setting` / `set_setting` | 3, 9, 10 |

### Placeholder scan

No TBD/TODO steps. Task 15 Holdings/Performance/charts now have full code. Chart components intentionally minimal SVG. Segment hard-filter deferred (observe `flagged_rows`). Task 8 split into 8a/8b/8c.

### Type consistency

- Setting keys: `kite_access_token`, `kite_token_updated_at`, `last_sync_at`, `last_trade_append_at`
- Settings API: `get_setting` / `set_setting` (public)
- Excess: `absolute_excess_pp` vs point-to-point bench %; `cagr_excess_pp` vs bench CAGR; `xirr_excess_pp` vs `benchmark_xirr_from_trades` — `excess_pp = (port - peer) * 100`
- Windows: `windows: { ITD, 1Y, 3Y, 5Y }` on overview **and** holdings; `null` when insufficient history
- Import result: `{format, new, existing, segment_counts, flagged_rows, date_min, date_max}`
- Holding / Overview / Performance field names match web `types.ts`
- Redirect URL: web `/auth/callback` (Task 14)
- Smallcap Yahoo ticker: `NIFTYSMLCAP250.NS`

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-01-portfolio-tracker.md`. Two execution options:

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
