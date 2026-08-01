# API Live Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exercise every FastAPI endpoint against a real local SQLite DB, real Zerodha Console CSVs, live Kite OAuth, and live Yahoo/AMFI prices — find bugs before any frontend work — then fix them as bite-sized tasks.

**Architecture:** Run `apps/api` on port 8000 against `data/portfolio.db`. Drive the full first-run flow with curl (and one browser step for Kite OAuth). Console tradebook exports are **≤365 days**, typically cut by **Indian financial year (FY Apr–Mar)**, and **equity vs MF are separate downloads**. The API must accept **multi-file import in one request**, merge idempotently, and on any bad file **reject that file with a clear “fix and import again” message** without silently applying partial bad rows. Known route gaps are fixed first; then multi-file import; then live smoke. Bugs from the live run become fix tasks before frontend (main plan Tasks 12–16).

**Tech Stack:** FastAPI, SQLite, Kite Connect Personal, Console CSV, Yahoo Finance (`yfinance`), AMFI, curl, pytest, uv

## Global Constraints

- Never commit `.env`, CSVs with personal trades, access tokens, or `data/portfolio.db`
- CI must not use real Zerodha keys; live checks stay local/manual
- No secrets in logs or API response bodies (access_token never returned)
- Rates are fractions (`0.256` = 25.6%); excess is percentage points
- Windows: ITD / 1Y / 3Y / 5Y; null when N/A
- CSV import is all-or-nothing **per file** (bad rows → whole file rejected; other files in the same batch still accepted)
- Wrong / unrecognized input → HTTP 400 (single) or per-file `ok: false` (batch) with actionable `action` text telling the user to re-export and **import again** — never write partial rows from a bad file
- Multi-file import is a first-class API: users upload several FY / ≤365-day EQ and MF CSVs together
- Console limitation (product fact): tradebook export date range max **365 days**; Equity and Mutual Funds exported as **separate** CSVs; users commonly export **one FY per file**
- Indian FY label: `FY2024-25` = 2024-04-01 → 2025-03-31 (inclusive)
- Market may be closed (weekend/holiday): holdings sync + price refresh still required; today's trade append may be 0

---

## Prerequisites (what the engineer must provide)

Do **not** start Task 4 (live smoke) until these exist on the machine:

| # | Item | Why |
|---|------|-----|
| 1 | Kite Connect **Personal** app `api_key` + `api_secret` | OAuth + `/sync` |
| 2 | Redirect URL registered in [Kite developer console](https://developers.kite.trade/) as **exactly** `http://127.0.0.1:8000/auth/callback` | Token exchange after login |
| 3 | Repo-root `.env` with keys filled (copy from `.env.example`) | App config — **done** |
| 4 | Multiple Console **equity** tradebook CSVs covering history in ≤365-day slices | History / XIRR / reconcile |
| 5 | Multiple Console **MF** tradebook CSVs (separate from equity) | MF import + AMFI NAVs |
| 6 | Rough Console sanity numbers (total value ±5%, 1–2 symbols with qty) | Catch wrong metrics early |
| 7 | Interactive browser available in the same session | Click Kite login once |

### Locked live CSV set (local Downloads — never commit)

Headers on all files match fixtures:  
`symbol,isin,trade_date,exchange,segment,series,trade_type,auction,quantity,price,trade_id,order_id,order_execution_time`

| File | Segment | Approx FY | Rows | Date span |
|------|---------|-----------|------|-----------|
| `…/tradebook-RYY010-EQ (2).csv` | EQ | FY2023-24 (partial) | 72 | 2024-01-04 → 2024-03-28 |
| `…/tradebook-RYY010-EQ (1).csv` | EQ | FY2024-25 | 680 | 2024-04-02 → 2025-03-11 |
| `…/tradebook-RYY010-EQ.csv` | EQ | FY2025-26 (partial) | 98 | 2025-04-03 → 2026-01-22 |
| `…/tradebook-RYY010-MF.csv` | MF | FY2023-24 | 47 | 2023-07-26 → 2024-03-27 |
| `…/tradebook-RYY010-MF (1).csv` | MF | FY2024-25 | 129 | 2024-04-01 → 2025-03-21 |
| `…/tradebook-RYY010-MF (2).csv` | MF | FY2025-26 (partial) | 85 | 2025-04-07 → 2026-03-05 |
| `…/tradebook-RYY010-MF (3).csv` | MF | same as MF (2) | 85 | **duplicate** — skip or idempotency only |

Full paths remain under `/Users/subrahmanian@backbase.com/Downloads/` (never commit).

**Combined coverage after all unique imports:**
- Equity transactions: ~2024-01-04 → 2026-01-22
- MF transactions: ~2023-07-26 → 2026-03-05

**Expected history gaps (not necessarily code bugs):**
- Equity CSV ends **2026-01-22**; smoke date is **2026-08-01** → ~6 months missing equity trades unless a newer slice is exported
- MF CSV ends **2026-03-05** → ~5 months missing MF trades
- Gap/reconcile alerts after `/sync` are **expected** until a fresh ≤365-day export covers “last CSV end → today”. Optional follow-up: export one more EQ slice and one more MF slice for the latest window before trusting XIRR fully.

Import order does not matter (dedupe keys). Prefer FY chronological for easier log reading. Prefer **one multi-file request** over many single-file calls once Task 2 lands.

---

## File Structure

| Path | Responsibility |
|------|----------------|
| `.env` (gitignored) | Live Kite keys + redirect; engineer creates |
| `data/portfolio.db` (gitignored) | Live SQLite created by `init_db` on API start |
| `apps/api/src/portfolio_tracker/routers/portfolio.py` | Add missing `GET /portfolio/performance` |
| `apps/api/src/portfolio_tracker/routers/auth.py` | Add `GET /auth/callback` so Kite browser redirect can exchange token without a web app |
| `apps/api/src/portfolio_tracker/modules/csv_import.py` | Per-file import + FY labels + actionable error helpers; batch merge |
| `apps/api/src/portfolio_tracker/routers/import_.py` | Single-file + multi-file upload; wrong-input → re-import guidance |
| `apps/api/tests/test_csv_import.py` | Multi-file, partial failure, FY label, wrong-input message tests |
| `apps/api/tests/test_api_integration.py` | Route-level tests for performance + GET callback + multi import |
| `apps/api/tests/test_kite_auth.py` | Unit coverage for GET callback exchange path |
| `docs/superpowers/manual/2026-08-01-live-smoke-checklist.md` | Step-by-step curl runbook + expected checks |
| `docs/superpowers/manual/2026-08-01-live-findings.md` | Bug log from the live run (inputs for later fix tasks) |
| `scripts/live_smoke.sh` | One multi-file import of all EQ/MF FY slices, then sync/read |

Endpoints in scope:

```
GET  /health
GET  /auth/login-url
GET  /auth/callback?request_token=…   ← Task 1
POST /auth/callback
GET  /auth/status
POST /auth/logout
POST /import/csv                      ← single file (kept) OR multi via files= (Task 2)
POST /sync
GET  /portfolio/overview
GET  /portfolio/holdings
GET  /portfolio/alerts
GET  /portfolio/performance           ← Task 1
GET  /settings/benchmarks
PUT  /settings/benchmarks/{id}
PUT  /settings/categories/{id}
```

---

### Task 1: Mount missing performance route + GET OAuth callback

**Why first:** Live smoke cannot hit performance over HTTP today (`get_performance` exists; router does not). Kite redirects with **GET** query params; only `POST /auth/callback` exists, so a browser landing on the API URL gets 405 without a frontend.

**Files:**
- Modify: `apps/api/src/portfolio_tracker/routers/portfolio.py`
- Modify: `apps/api/src/portfolio_tracker/routers/auth.py`
- Modify: `apps/api/tests/test_api_integration.py`
- Modify: `apps/api/tests/test_kite_auth.py`

**Interfaces:**
- Consumes: `portfolio.get_performance(session, as_of: str) -> dict`
- Consumes: `kite_auth.exchange_request_token(session, request_token: str) -> dict[str, bool]`
- Produces: `GET /portfolio/performance` → same shape as `get_performance`
- Produces: `GET /auth/callback?request_token=&status=` → `{"connected": true}` on success; 400/401 on failure (same semantics as POST)

- [ ] **Step 1: Write the failing tests**

Append to `apps/api/tests/test_api_integration.py`:

```python
def test_portfolio_performance_route_returns_contributors(monkeypatch):
    monkeypatch.setattr(
        "portfolio_tracker.modules.kite_auth.authenticated_kite",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Kite must not be called")
        ),
    )
    client = TestClient(create_app())
    csv_text = (FIXTURES / "equity_tradebook.csv").read_text()
    client.post(
        "/import/csv",
        files={"file": ("equity.csv", csv_text, "text/csv")},
    )
    as_of = date.today().isoformat()
    Session = get_session_factory()
    with Session() as session:
        session.add_all(
            [
                Price(symbol="RELIANCE.NS", price_date="2024-01-15", close=2500.0, source="yahoo"),
                Price(symbol="RELIANCE.NS", price_date=as_of, close=3000.0, source="yahoo"),
                Price(symbol="INFY.NS", price_date="2024-02-01", close=1500.0, source="yahoo"),
                Price(symbol="INFY.NS", price_date=as_of, close=1800.0, source="yahoo"),
                BenchmarkPrice(index_symbol="Nifty 500", price_date="2024-01-15", close=10000.0),
                BenchmarkPrice(index_symbol="Nifty 500", price_date=as_of, close=12000.0),
            ]
        )
        session.commit()

    response = client.get("/portfolio/performance")
    assert response.status_code == 200
    body = response.json()
    assert body["default_window"] == "ITD"
    assert "overview" in body
    assert "contributors" in body
    assert "holdings" in body
    assert "windows_available" in body
```

Append to `apps/api/tests/test_kite_auth.py` (or integration file if preferred):

```python
def test_auth_callback_get_exchanges_request_token(monkeypatch):
    from portfolio_tracker.main import create_app
    from fastapi.testclient import TestClient

    monkeypatch.setenv("KITE_API_KEY", "test_key")
    monkeypatch.setenv("KITE_API_SECRET", "test_secret")
    # Clear settings cache if present
    from portfolio_tracker.config import get_settings
    get_settings.cache_clear()

    def fake_exchange(session, request_token: str):
        assert request_token == "req_abc"
        return {"connected": True}

    monkeypatch.setattr(
        "portfolio_tracker.modules.kite_auth.exchange_request_token",
        fake_exchange,
    )
    client = TestClient(create_app())
    response = client.get("/auth/callback", params={"request_token": "req_abc", "status": "success"})
    assert response.status_code == 200
    assert response.json() == {"connected": True}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/api && uv run pytest tests/test_api_integration.py::test_portfolio_performance_route_returns_contributors tests/test_kite_auth.py::test_auth_callback_get_exchanges_request_token -v`

Expected: FAIL — performance 404 / GET callback 405 or missing

- [ ] **Step 3: Minimal implementation**

In `apps/api/src/portfolio_tracker/routers/portfolio.py`, add:

```python
@router.get("/performance")
def performance(session: Annotated[Session, Depends(get_db)]) -> dict:
    return portfolio.get_performance(session, as_of=date.today().isoformat())
```

In `apps/api/src/portfolio_tracker/routers/auth.py`, add GET alongside existing POST (share exchange logic):

```python
@router.get("/callback")
def callback_get(
    request_token: str,
    session: Session = Depends(get_db),
    status: str | None = None,
) -> dict[str, bool]:
    if status and status.lower() not in {"success", "ok"}:
        raise HTTPException(status_code=401, detail="Token exchange failed")
    try:
        return kite_auth.exchange_request_token(session, request_token)
    except kite_auth.KiteConfigError as exc:
        raise HTTPException(status_code=400, detail="Kite API credentials are not configured") from exc
    except kite_auth.KiteAuthError as exc:
        raise HTTPException(status_code=401, detail="Token exchange failed") from exc
```

Keep `POST /auth/callback` unchanged (web client will use it later).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd apps/api && uv run pytest tests/test_api_integration.py tests/test_kite_auth.py -v`

Expected: PASS (plus existing suite green)

Also: `cd apps/api && uv run pytest -v` — all collected tests PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/portfolio_tracker/routers/portfolio.py \
  apps/api/src/portfolio_tracker/routers/auth.py \
  apps/api/tests/test_api_integration.py \
  apps/api/tests/test_kite_auth.py
git commit -m "feat: expose performance route and GET OAuth callback for live smoke"
```

---

### Task 2: Multi-file CSV import + wrong-input re-import guidance

**Why:** Users export Console tradebooks by **financial year** (and EQ/MF separately), so one session needs many files. Wrong uploads must be **flagged per file** with “import again” guidance — never silent partial writes from a bad file.

**Files:**
- Modify: `apps/api/src/portfolio_tracker/modules/csv_import.py`
- Modify: `apps/api/src/portfolio_tracker/routers/import_.py`
- Modify: `apps/api/tests/test_csv_import.py`

**Interfaces:**
- Consumes: existing `import_csv(session, text) -> ImportResult`
- Produces:
  - `financial_year_label(iso_date: str) -> str` — e.g. `"2024-04-02"` → `"FY2024-25"`
  - `financial_years_spanned(date_min: str | None, date_max: str | None) -> list[str]`
  - `REIMPORT_ACTION` constant (exact string below)
  - `import_csv_batch(session, files: list[tuple[str, str]]) -> BatchImportResult` where each item is `(filename, utf8_text)`
  - `POST /import/csv` accepts **one or more** multipart parts named `files` (preferred) and still accepts legacy single part `file` for compatibility
  - Batch response shape:

```python
class FileImportOk(TypedDict):
    filename: str
    ok: Literal[True]
    format: FormatName
    new: int
    existing: int
    segment_counts: dict[str, int]
    flagged_rows: list[str]
    date_min: str | None
    date_max: str | None
    financial_years: list[str]  # e.g. ["FY2024-25"]

class FileImportErr(TypedDict):
    filename: str
    ok: Literal[False]
    code: Literal["encoding", "csv_format", "csv_parse", "empty"]
    message: str
    errors: list[str]
    action: str  # always REIMPORT_ACTION

class BatchImportResult(TypedDict):
    files: list[FileImportOk | FileImportErr]
    summary: dict  # accepted, rejected, new, existing
```

`REIMPORT_ACTION` (verbatim):

```text
This file was not imported. Export again from Zerodha Console → Reports → Tradebook (Equity or Mutual Funds), use a ≤365-day or financial-year window, UTF-8 CSV, then import this file again. Other files in the same upload are unaffected.
```

Single-file legacy: when only `file=` is sent, keep returning bare `ImportResult` **plus** `financial_years` on success; on error return 400 with `detail` object `{message, errors?, action: REIMPORT_ACTION}`.

- [ ] **Step 1: Write the failing tests**

Append to `apps/api/tests/test_csv_import.py`:

```python
def test_financial_year_label_uses_indian_fy():
    assert csv_import.financial_year_label("2024-03-31") == "FY2023-24"
    assert csv_import.financial_year_label("2024-04-01") == "FY2024-25"
    assert csv_import.financial_years_spanned("2024-01-04", "2024-03-28") == ["FY2023-24"]
    assert csv_import.financial_years_spanned("2024-04-02", "2025-03-11") == ["FY2024-25"]


def test_batch_import_accepts_multiple_files_and_skips_duplicates():
    eq = (FIXTURES / "equity_tradebook.csv").read_text()
    mf = (FIXTURES / "mf_tradebook.csv").read_text()
    Session = get_session_factory()
    with Session() as session:
        result = csv_import.import_csv_batch(
            session,
            [
                ("equity.csv", eq),
                ("mf.csv", mf),
                ("equity-again.csv", eq),
            ],
        )
        session.commit()
        assert result["summary"]["accepted"] == 3
        assert result["summary"]["rejected"] == 0
        assert result["summary"]["new"] == 3  # 2 equity + 1 mf; third file all existing
        assert result["summary"]["existing"] == 2
        assert result["files"][0]["ok"] is True
        assert result["files"][0]["financial_years"]
        assert session.query(Transaction).count() == 3


def test_batch_import_rejects_bad_file_keeps_good_files():
    eq = (FIXTURES / "equity_tradebook.csv").read_text()
    Session = get_session_factory()
    with Session() as session:
        result = csv_import.import_csv_batch(
            session,
            [
                ("equity.csv", eq),
                ("bad.csv", "not,a,tradebook\n1,2,3\n"),
            ],
        )
        session.commit()
        assert result["summary"]["accepted"] == 1
        assert result["summary"]["rejected"] == 1
        bad = result["files"][1]
        assert bad["ok"] is False
        assert bad["code"] == "csv_format"
        assert bad["action"] == csv_import.REIMPORT_ACTION
        assert "import this file again" in bad["action"].lower()
        assert session.query(Transaction).count() == 2


def test_import_route_multi_file_and_wrong_input_action():
    from portfolio_tracker.main import create_app

    client = TestClient(create_app())
    eq = (FIXTURES / "equity_tradebook.csv").read_bytes()
    bad = b"foo,bar\n1,2\n"
    response = client.post(
        "/import/csv",
        files=[
            ("files", ("equity.csv", eq, "text/csv")),
            ("files", ("bad.csv", bad, "text/csv")),
        ],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["accepted"] == 1
    assert body["summary"]["rejected"] == 1
    assert body["files"][1]["action"] == csv_import.REIMPORT_ACTION

    single_bad = client.post(
        "/import/csv",
        files={"file": ("bad.csv", bad, "text/csv")},
    )
    assert single_bad.status_code == 400
    detail = single_bad.json()["detail"]
    assert isinstance(detail, dict)
    assert detail["action"] == csv_import.REIMPORT_ACTION
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/api && uv run pytest tests/test_csv_import.py::test_financial_year_label_uses_indian_fy tests/test_csv_import.py::test_batch_import_accepts_multiple_files_and_skips_duplicates tests/test_csv_import.py::test_batch_import_rejects_bad_file_keeps_good_files tests/test_csv_import.py::test_import_route_multi_file_and_wrong_input_action -v`

Expected: FAIL (batch API / FY helpers missing)

- [ ] **Step 3: Minimal implementation**

Add to `apps/api/src/portfolio_tracker/modules/csv_import.py` (keep existing helpers; extend `ImportResult`):

```python
REIMPORT_ACTION = (
    "This file was not imported. Export again from Zerodha Console → Reports → "
    "Tradebook (Equity or Mutual Funds), use a ≤365-day or financial-year window, "
    "UTF-8 CSV, then import this file again. Other files in the same upload are unaffected."
)


def financial_year_label(iso_date: str) -> str:
    d = date.fromisoformat(iso_date[:10])
    start_year = d.year if d.month >= 4 else d.year - 1
    return f"FY{start_year}-{str(start_year + 1)[-2:]}"


def financial_years_spanned(date_min: str | None, date_max: str | None) -> list[str]:
    if not date_min or not date_max:
        return []
    start = date.fromisoformat(date_min[:10])
    end = date.fromisoformat(date_max[:10])
    labels: list[str] = []
    year = start.year if start.month >= 4 else start.year - 1
    while True:
        fy_start = date(year, 4, 1)
        fy_end = date(year + 1, 3, 31)
        if fy_end < start:
            year += 1
            continue
        if fy_start > end:
            break
        labels.append(f"FY{year}-{str(year + 1)[-2:]}")
        year += 1
    return labels
```

In `import_csv` return dict, add:

```python
"financial_years": financial_years_spanned(
    min(dates) if dates else None,
    max(dates) if dates else None,
),
```

Add TypedDicts + batch function:

```python
class FileImportOk(TypedDict):
    filename: str
    ok: Literal[True]
    format: FormatName
    new: int
    existing: int
    segment_counts: dict[str, int]
    flagged_rows: list[str]
    date_min: str | None
    date_max: str | None
    financial_years: list[str]


class FileImportErr(TypedDict):
    filename: str
    ok: Literal[False]
    code: Literal["encoding", "csv_format", "csv_parse", "empty"]
    message: str
    errors: list[str]
    action: str


class BatchImportResult(TypedDict):
    files: list[FileImportOk | FileImportErr]
    summary: dict[str, int]


def import_csv_batch(
    session: Session, files: list[tuple[str, str]]
) -> BatchImportResult:
    out: list[FileImportOk | FileImportErr] = []
    total_new = 0
    total_existing = 0
    accepted = 0
    rejected = 0
    for filename, text in files:
        if not text.strip():
            rejected += 1
            out.append(
                {
                    "filename": filename,
                    "ok": False,
                    "code": "empty",
                    "message": "CSV file is empty",
                    "errors": [],
                    "action": REIMPORT_ACTION,
                }
            )
            continue
        nested = session.begin_nested()
        try:
            result = import_csv(session, text)
            nested.commit()
            accepted += 1
            total_new += result["new"]
            total_existing += result["existing"]
            out.append({"filename": filename, "ok": True, **result})
        except CsvFormatError as exc:
            nested.rollback()
            rejected += 1
            out.append(
                {
                    "filename": filename,
                    "ok": False,
                    "code": "csv_format",
                    "message": str(exc),
                    "errors": [],
                    "action": REIMPORT_ACTION,
                }
            )
        except CsvParseError as exc:
            nested.rollback()
            rejected += 1
            out.append(
                {
                    "filename": filename,
                    "ok": False,
                    "code": "csv_parse",
                    "message": str(exc),
                    "errors": exc.errors,
                    "action": REIMPORT_ACTION,
                }
            )
    return {
        "files": out,
        "summary": {
            "accepted": accepted,
            "rejected": rejected,
            "new": total_new,
            "existing": total_existing,
        },
    }
```

Replace `apps/api/src/portfolio_tracker/routers/import_.py` body with:

```python
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from portfolio_tracker.db.session import get_db
from portfolio_tracker.modules import csv_import

router = APIRouter(prefix="/import", tags=["import"])


def _bad_detail(message: str, errors: list[str] | None = None) -> dict:
    return {
        "message": message,
        "errors": errors or [],
        "action": csv_import.REIMPORT_ACTION,
    }


@router.post(
    "/csv",
    responses={400: {"description": "Invalid CSV (single-file mode)"}},
)
async def import_csv_endpoint(
    session: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile | None, File()] = None,
    files: Annotated[list[UploadFile] | None, File()] = None,
) -> dict:
    uploads: list[UploadFile] = []
    if files:
        uploads.extend(files)
    if file is not None:
        uploads.append(file)
    if not uploads:
        raise HTTPException(status_code=400, detail=_bad_detail("No CSV file provided"))

    use_batch = bool(files) or len(uploads) > 1
    if use_batch:
        decoded: list[tuple[str, str]] = []
        early: list[csv_import.FileImportErr] = []
        for upload in uploads:
            name = upload.filename or "upload.csv"
            raw = await upload.read()
            try:
                decoded.append((name, raw.decode("utf-8-sig")))
            except UnicodeDecodeError:
                early.append(
                    {
                        "filename": name,
                        "ok": False,
                        "code": "encoding",
                        "message": "File must be UTF-8 CSV",
                        "errors": [],
                        "action": csv_import.REIMPORT_ACTION,
                    }
                )
        batch = csv_import.import_csv_batch(session, decoded)
        if early:
            batch["files"] = [*early, *batch["files"]]
            batch["summary"]["rejected"] += len(early)
        return batch

    upload = uploads[0]
    raw = await upload.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400, detail=_bad_detail("File must be UTF-8 CSV")
        ) from exc
    try:
        return csv_import.import_csv(session, text)
    except csv_import.CsvFormatError as exc:
        raise HTTPException(status_code=400, detail=_bad_detail(str(exc))) from exc
    except csv_import.CsvParseError as exc:
        raise HTTPException(
            status_code=400, detail=_bad_detail(str(exc), exc.errors)
        ) from exc
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd apps/api && uv run pytest tests/test_csv_import.py -v`

Expected: PASS (fix any older asserts that omit `financial_years`).

Also: `cd apps/api && uv run pytest -v` — full suite PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/portfolio_tracker/modules/csv_import.py \
  apps/api/src/portfolio_tracker/routers/import_.py \
  apps/api/tests/test_csv_import.py
git commit -m "feat: multi-file CSV import with per-file re-import errors and FY labels"
```

---

### Task 3: Live smoke runbook + curl script

**Files:**
- Create: `docs/superpowers/manual/2026-08-01-live-smoke-checklist.md`
- Create: `docs/superpowers/manual/2026-08-01-live-findings.md`
- Create: `scripts/live_smoke.sh`

**Interfaces:**
- Consumes: API on `http://127.0.0.1:8000`
- Produces: checklist with pass/fail boxes; findings template; script that runs non-interactive steps after OAuth

- [ ] **Step 1: Write findings template**

Create `docs/superpowers/manual/2026-08-01-live-findings.md`:

```markdown
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
```

- [ ] **Step 2: Write checklist**

Create `docs/superpowers/manual/2026-08-01-live-smoke-checklist.md` with the exact commands from Task 4 Steps (copy the curl blocks so a human can run offline). Include:

1. `.env` ready; redirect URL matches Kite console
2. `rm -f data/portfolio.db` for a clean first run (recommended)
3. Start API: `npm run api` from repo root
4. Multi-file `POST /import/csv` with `files=` for all EQ/MF FY slices; verify wrong-input `action` path once
5. Each endpoint check with Expected JSON shape notes
6. On any failure → append row to findings; do not invent fixes mid-run unless blocking
7. Document expected gap after last CSV `date_max` → today

- [ ] **Step 3: Write `scripts/live_smoke.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
BASE="${BASE_URL:-http://127.0.0.1:8000}"
DL="${DOWNLOADS_DIR:-$HOME/Downloads}"

# Console: ≤365 days / typically one Indian FY per file; EQ and MF separate.
# Multi-file one-shot via repeated multipart field name `files`.
EQUITY_CSVS=(
  "${DL}/tradebook-RYY010-EQ (2).csv"
  "${DL}/tradebook-RYY010-EQ (1).csv"
  "${DL}/tradebook-RYY010-EQ.csv"
)
# MF (3) omitted — duplicate of MF (2)
MF_CSVS=(
  "${DL}/tradebook-RYY010-MF.csv"
  "${DL}/tradebook-RYY010-MF (1).csv"
  "${DL}/tradebook-RYY010-MF (2).csv"
)

echo "== health =="
curl -sf "$BASE/health" | tee /tmp/pt-health.json
grep -q '"status":"ok"' /tmp/pt-health.json

echo "== auth status (pre) =="
curl -sf "$BASE/auth/status" | tee /tmp/pt-auth-status.json

FORM_ARGS=()
for f in "${EQUITY_CSVS[@]}" "${MF_CSVS[@]}"; do
  test -f "$f" || { echo "MISSING: $f"; exit 1; }
  FORM_ARGS+=(-F "files=@${f};type=text/csv")
done

echo "== multi-file import (EQ + MF FY slices) =="
curl -sf -X POST "$BASE/import/csv" "${FORM_ARGS[@]}" | tee /tmp/pt-import-batch.json
# Fail smoke if any file rejected (wrong input)
python3 - <<'PY'
import json, sys
body = json.load(open("/tmp/pt-import-batch.json"))
assert "summary" in body, body
if body["summary"]["rejected"]:
    for row in body["files"]:
        if not row.get("ok", True):
            print("REJECTED", row.get("filename"), row.get("code"), row.get("action", "")[:80])
    sys.exit(1)
print("accepted", body["summary"]["accepted"], "new", body["summary"]["new"])
for row in body["files"]:
    print(row["filename"], row.get("financial_years"), "new=", row.get("new"))
PY

echo "== re-import one EQ slice via single file= (idempotent) =="
curl -sf -X POST "$BASE/import/csv" \
  -F "file=@${EQUITY_CSVS[-1]};type=text/csv" | tee /tmp/pt-import-eq-re.json

echo "== sync =="
curl -sf -X POST "$BASE/sync" | tee /tmp/pt-sync.json

echo "== portfolio =="
curl -sf "$BASE/portfolio/overview" | tee /tmp/pt-overview.json
curl -sf "$BASE/portfolio/holdings" | tee /tmp/pt-holdings.json
curl -sf "$BASE/portfolio/alerts" | tee /tmp/pt-alerts.json
curl -sf "$BASE/portfolio/performance" | tee /tmp/pt-performance.json

echo "== settings =="
curl -sf "$BASE/settings/benchmarks" | tee /tmp/pt-benchmarks.json

echo "OK — inspect /tmp/pt-*.json and fill live-findings.md"
echo "NOTE: CSV coverage may end before today; gap/reconcile alerts can be expected."
```

Make executable: `chmod +x scripts/live_smoke.sh`

- [ ] **Step 4: Commit docs + script only**

```bash
git add docs/superpowers/manual/2026-08-01-live-smoke-checklist.md \
  docs/superpowers/manual/2026-08-01-live-findings.md \
  scripts/live_smoke.sh
git commit -m "docs: add live API smoke checklist and curl script"
```

---

### Task 4: Execute live smoke with real credentials + CSVs

**Files:**
- Modify (local only): `.env`, `data/portfolio.db` — never commit
- Modify: `docs/superpowers/manual/2026-08-01-live-findings.md` (fill results; scrub secrets)

**Interfaces:**
- Consumes: prerequisites table; Task 1 routes; Task 2 multi-file import; Task 3 script
- Produces: completed findings file with pass/fail + bug table

- [ ] **Step 1: Confirm prerequisites**

```bash
test -f .env && grep -q 'KITE_API_KEY=.\+' .env && echo "keys present" || echo "MISSING KEYS"
DL="$HOME/Downloads"
for f in \
  "tradebook-RYY010-EQ (2).csv" \
  "tradebook-RYY010-EQ (1).csv" \
  "tradebook-RYY010-EQ.csv" \
  "tradebook-RYY010-MF.csv" \
  "tradebook-RYY010-MF (1).csv" \
  "tradebook-RYY010-MF (2).csv"
do
  test -f "$DL/$f" && echo "ok $f" || echo "MISSING $f"
done
```

Expected: keys present; all six unique slice files ok (`MF (3)` optional duplicate). Stop if any unique file missing.

- [ ] **Step 2: Fresh DB + start API**

```bash
mkdir -p data
rm -f data/portfolio.db
npm run api
```

In another terminal:

```bash
curl -sf http://127.0.0.1:8000/health
```

Expected: `{"status":"ok"}` and `data/portfolio.db` created.

- [ ] **Step 3: OAuth (interactive)**

```bash
curl -sf http://127.0.0.1:8000/auth/login-url
# Open login_url in browser; complete Zerodha login
# Browser lands on http://127.0.0.1:8000/auth/callback?request_token=…&action=login&status=success
# Page/body should show {"connected":true}
curl -sf http://127.0.0.1:8000/auth/status
```

Expected status:

```json
{
  "connected": true,
  "credentials_configured": true,
  "last_sync_at": null,
  "last_trade_append_at": null
}
```

If GET callback fails: copy `request_token` from the URL and:

```bash
curl -sf -X POST http://127.0.0.1:8000/auth/callback \
  -H 'Content-Type: application/json' \
  -d '{"request_token":"PASTE_TOKEN"}'
```

Log any failure as finding `F-auth-*`.

- [ ] **Step 4: Multi-file import (EQ + MF FY slices)**

After OAuth, prefer one multi-file request (Task 2):

```bash
./scripts/live_smoke.sh
```

Or manually:

```bash
BASE=http://127.0.0.1:8000
DL="$HOME/Downloads"
curl -sf -X POST "$BASE/import/csv" \
  -F "files=@${DL}/tradebook-RYY010-EQ (2).csv;type=text/csv" \
  -F "files=@${DL}/tradebook-RYY010-EQ (1).csv;type=text/csv" \
  -F "files=@${DL}/tradebook-RYY010-EQ.csv;type=text/csv" \
  -F "files=@${DL}/tradebook-RYY010-MF.csv;type=text/csv" \
  -F "files=@${DL}/tradebook-RYY010-MF (1).csv;type=text/csv" \
  -F "files=@${DL}/tradebook-RYY010-MF (2).csv;type=text/csv" \
  | tee /tmp/pt-import-batch.json
```

Expected: HTTP 200; `summary.rejected` = 0; `summary.accepted` = 6; each file has `financial_years` (FY labels); `new` sums to total unique trades.

**Wrong-input check (must flag + ask re-import):**

```bash
curl -s -X POST "$BASE/import/csv" \
  -F "files=@${DL}/tradebook-RYY010-EQ.csv;type=text/csv" \
  -F "files=@/etc/hosts;type=text/csv" | tee /tmp/pt-import-partial.json
```

Expected: HTTP 200; `summary.accepted` ≥ 1; `summary.rejected` ≥ 1; rejected row has `action` containing `import this file again`; good file still imported (or idempotent). Single bad `file=` alone → HTTP 400 with same `action`.

Idempotency: re-send the batch or one `file=` → `new` = 0 for already-seen rows.

Optional: export one more EQ window **2026-01-23 → today** and MF **2026-03-06 → today** for tighter reconcile — not required to finish smoke.

- [ ] **Step 5: Sync + prices**

Already in script; or:

```bash
curl -sf -X POST http://127.0.0.1:8000/sync
```

Expected:
- `holdings_count` ≈ Console holdings count
- `prices.updated` > 0 or failures listed in `prices.failed` (log each failed symbol)
- `last_sync_at` set on subsequent `/auth/status`

- [ ] **Step 6: Read portfolio surfaces**

Check `/tmp/pt-overview.json`, holdings, alerts, performance:

| Check | Pass if |
|-------|---------|
| `total_value` | Within ~5% of Console **holdings value** (LTP/NAV lag OK). Do not require transaction-implied qty to match until latest CSV slices exist |
| holdings qty | Match Console for 2 spot-checked symbols **from Kite snapshot** after sync |
| `incomplete` | false when prices succeeded; true only with listed gaps |
| `windows.ITD` | non-null when history exists |
| `windows.1Y` / `3Y` / `5Y` | non-null only when inception allows (MF history from 2023 may unlock 1Y/3Y) |
| alerts.gap | **Expected** if `last_trade_append` / CSV `date_max` ≪ today — record suggested range; not a P0 by itself |
| alerts.reconcile | **Likely** until post-CSV trades are imported; file as P1 only if diffs remain after importing a fresh ≤365-day slice through today |
| performance.contributors | sorted; weights sum ≈ 1 for valued rows |
| rates | look like fractions (XIRR 0.18 not 18) |

- [ ] **Step 7: Settings round-trip**

```bash
# pick instrument_id from /settings/benchmarks
curl -sf -X PUT http://127.0.0.1:8000/settings/benchmarks/ID \
  -H 'Content-Type: application/json' \
  -d '{"benchmark_index":"Nifty Midcap 150"}'
curl -sf -X PUT http://127.0.0.1:8000/settings/categories/ID \
  -H 'Content-Type: application/json' \
  -d '{"category":"mid_cap"}'
curl -sf http://127.0.0.1:8000/settings/benchmarks
```

Expected: `source` = `user`; category updated; overview/holdings pick up new bench on next read.

- [ ] **Step 8: Logout gate**

```bash
curl -sf -X POST http://127.0.0.1:8000/auth/logout
curl -s -o /tmp/pt-sync-401.json -w "%{http_code}" -X POST http://127.0.0.1:8000/sync
```

Expected: HTTP `401`; body detail mentions reconnect. Re-login only if more testing needed.

- [ ] **Step 9: Fill findings + commit scrubbed log**

Update `docs/superpowers/manual/2026-08-01-live-findings.md` with results. **Strip** tokens, account ids, full holdings lists — keep symbols only if needed for repro.

```bash
git add docs/superpowers/manual/2026-08-01-live-findings.md
git commit -m "docs: record live API smoke results"
```

---

### Task 5: Triage findings → fix-task backlog

**Files:**
- Modify: `docs/superpowers/manual/2026-08-01-live-findings.md`
- Create: `docs/superpowers/plans/2026-08-01-api-live-fixes.md` (only if ≥1 bug)

**Interfaces:**
- Consumes: findings table from Task 4
- Produces: ordered fix plan (or "no bugs — proceed to frontend")

- [ ] **Step 1: Classify each finding**

| Severity | Meaning | Action |
|----------|---------|--------|
| P0 | Blocks first-run (auth, CSV import, sync 500, DB corrupt) | Fix before anything else |
| P1 | Wrong numbers / reconcile false positives / price mapping | Fix before frontend |
| P2 | Polish (missing field, noisy incomplete flag) | Fix before frontend if cheap; else note |
| P3 | Deferred / known (weekend empty trade append; Console 365-day export limit; duplicate MF download) | Document only |

- [ ] **Step 2: For each P0/P1, draft a fix task**

Each fix task in `docs/superpowers/plans/2026-08-01-api-live-fixes.md` must include:
- Exact failing behavior + repro curl
- Files to change
- Failing pytest (fixture or recorded header sample **without** personal quantities if possible)
- Minimal fix
- Commit message

Template:

```markdown
### Fix N: [short title]

**Files:**
- Modify: `path`
- Test: `path`

- [ ] Step 1: failing test (full code)
- [ ] Step 2: run — expect FAIL
- [ ] Step 3: fix (full code)
- [ ] Step 4: run — expect PASS + full suite
- [ ] Step 5: commit
- [ ] Step 6: re-run the single live curl that failed
```

- [ ] **Step 3: If zero P0/P1 bugs**

Write in findings: `Verdict: API ready for Task 12 frontend.` Commit that note. Do not create an empty fixes plan.

- [ ] **Step 4: Commit triage**

```bash
git add docs/superpowers/manual/2026-08-01-live-findings.md
# and fixes plan if created
git commit -m "docs: triage live API findings into fix tasks"
```

---

### Task 6: Execute fix tasks (placeholder gate)

**Files:** whatever Task 5 lists

**Interfaces:**
- Consumes: `2026-08-01-api-live-fixes.md`
- Produces: green unit/integration tests + re-verified live curls

- [ ] **Step 1: Implement fixes in severity order (P0 → P1 → P2)** using TDD per fix task

- [ ] **Step 2: After all fixes, optional second live pass**

```bash
rm -f data/portfolio.db
# re-auth, re-import, sync, overview spot-check
```

- [ ] **Step 3: Final verdict commit**

Update findings `Verdict:` line. Commit docs only.

---

## Self-Review

**1. Spec coverage:** Design §6 first-run + §7 errors + §8 manual tests map to Tasks 4–6. Auth, multi-file FY CSV (EQ + MF), wrong-input re-import guidance, sync, prices, portfolio, settings, logout covered. Performance HTTP + GET OAuth in Task 1. Multi-file import + FY labels in Task 2.

**2. Placeholder scan:** Task 6 depends on Task 5 output by design (unknown bugs). No TBD in Tasks 1–4. Fix-task template requires full code when written.

**3. Type consistency:** `get_performance(session, as_of)` return keys match route; `exchange_request_token` shared by GET/POST callback; batch `ImportResult` / `FileImportOk` include `financial_years`; `REIMPORT_ACTION` shared by single and batch error paths.

**Known risks entering the live run:**
- Real Console headers **already match** fixtures on the locked file set — header alias risk low for this run
- Weekend: `trades_appended` may be 0 — not a bug
- Yahoo symbol / AMFI ISIN mismatches → `prices.failed` / `incomplete: true`
- Holdings vs CSV reconcile diffs until a fresh ≤365-day / FY export covers **last CSV end → today** — expect gap/reconcile alerts; not automatically a code bug
- `MF (3)` duplicates `MF (2)` — skip or treat as idempotency check only
- Batch mode returns HTTP 200 with `summary.rejected > 0` for partial wrong input — UI must read `action`, not only status code

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-01-api-live-verification.md`. Two execution options:

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
