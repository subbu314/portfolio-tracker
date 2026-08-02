# API Deep Bug Hunt Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run a second, adversarial API verification pass that hunts bugs the first live smoke missed — empty states, auth edges, import edges, metric/window invariants, gap vs reconcile semantics, residual price identity — then triage findings into fix tasks before frontend.

**Architecture:** Keep the same local stack (`apps/api` on `:8000`, SQLite `data/portfolio.db`, real Kite + Console CSVs + Yahoo/AMFI). Do **not** repeat the happy-path-only smoke. Add an invariant auditor script that fails on structural contradictions (e.g. `3Y` present while `1Y` null). Drive empty-state and edge curls first on a fresh DB, then a full-data deep pass after OAuth + multi-file import + sync. Log every failure into a new findings file; triage into a new fixes plan.

**Tech Stack:** FastAPI, SQLite, Kite Connect Personal, Console CSV, Yahoo Finance, AMFI, curl, python3 (JSON auditors), pytest, uv

## Global Constraints

- Never commit `.env`, CSVs with personal trades, access tokens, or `data/portfolio.db`
- CI must not use real Zerodha keys; live checks stay local/manual
- No secrets in logs or API response bodies (`access_token` never returned)
- Rates are fractions (`0.256` = 25.6%); excess is percentage points
- Windows: ITD / 1Y / 3Y / 5Y; null when N/A
- CSV import is all-or-nothing **per file**
- Wrong / unrecognized input → HTTP 400 (single) or per-file `ok: false` (batch) with actionable `action` text
- Multi-file import is first-class; EQ and MF are separate Console downloads; max export window **365 days**
- Indian FY label: `FY2024-25` = 2024-04-01 → 2025-03-31 (inclusive)
- Market may be closed: holdings sync + price refresh still required; today's trade append may be 0
- First smoke already passed on tip `9acddf6` / merge `eb8f978` — this plan hunts **residuals and contradictions**, not re-proving basic connect→import→sync
- Known data gaps (not auto-bugs): EQ CSV ends ~2026-01-22; MF ends ~2026-03-05; Yahoo fails for SGB/delisted/DVR may remain

---

## Prerequisites

| # | Item | Why |
|---|------|-----|
| 1 | Repo-root `.env` with live Kite Personal keys | Auth + `/sync` |
| 2 | Redirect URL exactly `http://127.0.0.1:8000/auth/callback` | GET OAuth |
| 3 | Locked Consoles CSVs under `$HOME/Downloads` (same six unique slices as first smoke) | History |
| 4 | **Optional but high-value:** fresh EQ slice `2026-01-23 → today` and MF slice `2026-03-06 → today` | Tightens reconcile; isolates code bugs from data gaps |
| 5 | Rough Console total value (±5%) and 1–2 symbol qtys | Sanity |
| 6 | Interactive browser for one Kite login | OAuth |
| 7 | Prior findings available: `docs/superpowers/manual/2026-08-01-live-findings.md` | Avoid re-filing fixed F1–F7 |

### Locked CSV set (never commit)

Same as first smoke. Full paths under `/Users/subrahmanian@backbase.com/Downloads/`.

| File | Segment | Approx FY |
|------|---------|-----------|
| `tradebook-RYY010-EQ (2).csv` | EQ | FY2023-24 (partial) |
| `tradebook-RYY010-EQ (1).csv` | EQ | FY2024-25 |
| `tradebook-RYY010-EQ.csv` | EQ | FY2025-26 (partial) |
| `tradebook-RYY010-MF.csv` | MF | FY2023-24 |
| `tradebook-RYY010-MF (1).csv` | MF | FY2024-25 |
| `tradebook-RYY010-MF (2).csv` | MF | FY2025-26 (partial) |

Optional fresh slices (engineer exports before Task 4 if available):

| File env override | Segment | Window |
|-------------------|---------|--------|
| `$EQ_FRESH_CSV` | EQ | 2026-01-23 → as-of |
| `$MF_FRESH_CSV` | MF | 2026-03-06 → as-of |

---

## Why another pass (hypothesis backlog)

First smoke logged `windows: ITD + 3Y present; 1Y/5Y null`. Spec nesting: if inception allows `3Y`, `1Y` must also be eligible by calendar. Code path `_portfolio_window_benchmark_inputs` returns `None` for the **whole portfolio window** when **any** instrument has `qty > 0` at window start but missing opening price — so a short-history unpriced name can kill `1Y` while `3Y` still works (positions did not exist 3Y ago). That is a prime bug / product-defect candidate.

Other untested or weakly tested surfaces:

1. Empty DB responses (no connect, no import, no sync)
2. Auth callback `status=error` / missing `request_token` / reused token
3. Import edges: empty body, no files, binary garbage, equity-only, MF-only, duplicate batch
4. Double `/sync` idempotency; sync after logout already covered once
5. Settings override must change **excess numbers**, not only stored map
6. Gap alert uses `last_trade_append_at` set on every sync — may hide CSV history holes
7. Secrets leak scan on all JSON bodies
8. Residual: kite-only MF `symbol=ISIN`; Yahoo `TATAMTRDVR` / `TATAMOTORS` / `IDFC` / `TRIL` / SGB

---

## File Structure

| Path | Responsibility |
|------|----------------|
| `docs/superpowers/manual/2026-08-01-deep-smoke-checklist.md` | Step-by-step adversarial runbook |
| `docs/superpowers/manual/2026-08-01-deep-findings.md` | Bug log from this pass (scrubbed) |
| `scripts/deep_smoke.sh` | Empty-state + edge curls + full-data fetch |
| `scripts/audit_portfolio_invariants.py` | Fail-loud JSON invariant checks on `/tmp/pt-*.json` |
| `docs/superpowers/plans/2026-08-01-api-deep-fixes.md` | Created only if ≥1 P0/P1 found |
| Existing (read-only reference) | `scripts/live_smoke.sh`, first findings/checklist, API routers/modules |

Endpoints in scope (same surface; deeper assertions):

```
GET  /health
GET  /auth/login-url
GET  /auth/callback?request_token=&status=
POST /auth/callback
GET  /auth/status
POST /auth/logout
POST /import/csv
POST /sync
GET  /portfolio/overview
GET  /portfolio/holdings
GET  /portfolio/alerts
GET  /portfolio/performance
GET  /settings/benchmarks
PUT  /settings/benchmarks/{id}
PUT  /settings/categories/{id}
```

---

### Task 1: Deep checklist + invariant auditor + deep_smoke script

**Files:**
- Create: `docs/superpowers/manual/2026-08-01-deep-smoke-checklist.md`
- Create: `docs/superpowers/manual/2026-08-01-deep-findings.md`
- Create: `scripts/audit_portfolio_invariants.py`
- Create: `scripts/deep_smoke.sh`

**Interfaces:**
- Consumes: JSON files written by curls under `/tmp/pt-deep-*.json` (and `/tmp/pt-*.json` from `live_smoke.sh` when reused)
- Produces: non-zero exit + printed finding codes when invariants break; checklist/findings templates ready for Task 3–5

- [ ] **Step 1: Write findings template**

Create `docs/superpowers/manual/2026-08-01-deep-findings.md`:

```markdown
# Deep API findings — 2026-08-01

## Environment
- Date / time (IST):
- API commit SHA:
- Market open?:
- Fresh EQ/MF slices imported?: yes/no (basenames only)
- Console total value (approx):
- Prior smoke tip: `9acddf6` / merge `eb8f978`

## Checklist result
- [ ] Empty-state suite
- [ ] Auth edge suite
- [ ] Import edge suite
- [ ] Full-data invariant audit
- [ ] Settings excess delta
- [ ] Gap vs reconcile semantics
- [ ] Secrets scan
- [ ] Residual price / identity notes

## Bugs
| ID | Severity | Endpoint / area | Observed | Expected | Repro | Status |
|----|----------|-----------------|----------|----------|-------|--------|

## Triage
- Fix plan: (path or "none")

## Verdict
- (pending)
```

- [ ] **Step 2: Write invariant auditor**

Create `scripts/audit_portfolio_invariants.py`:

```python
#!/usr/bin/env python3
"""Fail-loud structural checks on portfolio JSON dumps from deep smoke.

Exit 0 = no invariant violations.
Exit 1 = one or more FINDING lines printed (treat as bug candidates).
Does not call the network; reads local JSON files only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RATE_KEYS = ("xirr", "cagr", "benchmark_return", "absolute_pct", "gain_pct")
EXCESS_KEYS = ("absolute_excess_pp", "xirr_excess_pp", "cagr_excess_pp")
WINDOW_ORDER = ("1Y", "3Y", "5Y")


def load(path: str) -> dict:
    return json.loads(Path(path).read_text())


def finding(code: str, detail: str) -> None:
    print(f"FINDING {code}: {detail}")


def check_rate_fraction(label: str, value, findings: list[str]) -> None:
    if value is None:
        return
    if not isinstance(value, (int, float)):
        findings.append(f"{label} not numeric: {value!r}")
        return
    # Rates are fractions. |rate| > 5 (~500%) is suspicious for annualized/ITD.
    if abs(value) > 5:
        findings.append(f"{label}={value} looks like percent not fraction")


def check_windows_nesting(windows: dict, label: str, findings: list[str]) -> None:
    """If a longer trailing window exists, shorter ones must also be eligible by calendar.

    Code may still null a shorter window for missing opening prices — that is a
    FINDING (product/defect), not silent OK.
    """
    present = {w: windows.get(w) is not None for w in WINDOW_ORDER}
    if present["3Y"] and not present["1Y"]:
        findings.append(f"{label}: 3Y present but 1Y null (window nesting)")
    if present["5Y"] and not present["3Y"]:
        findings.append(f"{label}: 5Y present but 3Y null (window nesting)")
    if present["5Y"] and not present["1Y"]:
        findings.append(f"{label}: 5Y present but 1Y null (window nesting)")


def scan_bundle(prefix: str, bundle: dict | None, findings: list[str]) -> None:
    if not bundle:
        return
    for key in RATE_KEYS:
        if key in bundle:
            check_rate_fraction(f"{prefix}.{key}", bundle.get(key), findings)
    abs_block = bundle.get("absolute")
    if isinstance(abs_block, dict):
        check_rate_fraction(f"{prefix}.absolute.gain_pct", abs_block.get("gain_pct"), findings)


def audit_overview(path: str) -> list[str]:
    findings: list[str] = []
    body = load(path)
    for key in ("xirr", "cagr", "benchmark_return"):
        check_rate_fraction(f"overview.{key}", body.get(key), findings)
    abs_block = body.get("absolute") or {}
    check_rate_fraction("overview.absolute.gain_pct", abs_block.get("gain_pct"), findings)
    for key in EXCESS_KEYS:
        val = body.get(key)
        if val is not None and abs(val) > 500:
            findings.append(f"overview.{key}={val} absurd for percentage points")

    total = body.get("total_value") or 0.0
    weights = [row.get("weight") or 0.0 for row in body.get("allocation") or []]
    if total > 0 and weights:
        wsum = sum(weights)
        if abs(wsum - 1.0) > 0.02:
            findings.append(f"overview.allocation weights sum={wsum} (want ≈1)")

    windows = body.get("windows") or {}
    check_windows_nesting(windows, "overview.windows", findings)
    for wname, wbody in windows.items():
        scan_bundle(f"overview.windows.{wname}", wbody, findings)

    invested = abs_block.get("invested_cost")
    current = abs_block.get("current_value")
    if invested is not None and current is not None and total > 0:
        if abs((current or 0) - total) > max(1.0, 0.001 * total):
            findings.append(
                f"overview.absolute.current_value={current} != total_value={total}"
            )
    return findings


def audit_holdings(path: str) -> list[str]:
    findings: list[str] = []
    body = load(path)
    rows = body.get("holdings") or []
    for row in rows:
        sym = row.get("symbol", "?")
        qty = row.get("qty")
        if qty is not None and abs(qty) < 1e-8 and qty != 0:
            findings.append(f"holdings[{sym}].qty dust not flattened: {qty}")
        if qty is not None and qty < 0:
            findings.append(f"holdings[{sym}].qty negative: {qty}")
        windows = row.get("windows") or {}
        check_windows_nesting(windows, f"holdings[{sym}].windows", findings)
        for wname, wbody in windows.items():
            scan_bundle(f"holdings[{sym}].windows.{wname}", wbody, findings)
        # Incomplete rows must not invent LTP-based value without ltp
        if row.get("ltp") is None and row.get("value") not in (None, 0, 0.0):
            if (row.get("qty") or 0) > 0:
                findings.append(f"holdings[{sym}] value set without ltp: {row.get('value')}")
    return findings


def audit_performance(path: str, overview_path: str) -> list[str]:
    findings: list[str] = []
    perf = load(path)
    overview = load(overview_path)
    nested = perf.get("overview") or {}
    if abs((nested.get("total_value") or 0) - (overview.get("total_value") or 0)) > 0.01:
        findings.append("performance.overview.total_value diverges from /portfolio/overview")
    avail = perf.get("windows_available") or []
    windows = nested.get("windows") or {}
    for w in avail:
        if windows.get(w) is None:
            findings.append(f"windows_available has {w} but overview.windows[{w}] is null")
    for w, body in windows.items():
        if body is not None and w not in avail and w != "ITD":
            # ITD always in windows dict; available list may omit ITD — only flag trailing
            if w in WINDOW_ORDER:
                findings.append(f"overview.windows[{w}] present but missing from windows_available")
    contrib = perf.get("contributors") or []
    prev = None
    for row in contrib:
        cur = row.get("absolute_excess_pp")
        if cur is None:
            continue
        if prev is not None and cur > prev + 1e-9:
            findings.append("contributors not sorted by absolute_excess_pp descending")
            break
        prev = cur
    wsum = sum((row.get("weight") or 0.0) for row in contrib if row.get("value"))
    # contributors may omit unpriced rows; only check if all valued holdings contribute
    return findings


def audit_secrets(*paths: str) -> list[str]:
    findings: list[str] = []
    banned = ("access_token", "api_secret", "request_token")
    for path in paths:
        text = Path(path).read_text().lower()
        for token in banned:
            # allow key names in error strings only if value-shaped secrets absent;
            # flag raw JWT-like or long hex blobs near token labels
            if f'"{token}"' in text and token != "request_token":
                # request_token may appear in docs; flag if present as JSON value key with long string
                pass
            if f'"{token}":' in text and token in ("access_token", "api_secret"):
                findings.append(f"{path} exposes JSON key {token}")
    return findings


def audit_alerts(path: str) -> list[str]:
    findings: list[str] = []
    body = load(path)
    gap = body.get("gap")
    reconcile = body.get("reconcile") or []
    # Soft note only when gap is null but reconcile is large — print as FINDING for triage
    if gap is None and len(reconcile) >= 10:
        findings.append(
            f"alerts.gap is null while reconcile has {len(reconcile)} diffs "
            "(gap may ignore CSV coverage holes when last_trade_append_at is today)"
        )
    return findings


def main(argv: list[str]) -> int:
    # Defaults match deep_smoke.sh outputs
    overview = argv[1] if len(argv) > 1 else "/tmp/pt-deep-overview.json"
    holdings = argv[2] if len(argv) > 2 else "/tmp/pt-deep-holdings.json"
    performance = argv[3] if len(argv) > 3 else "/tmp/pt-deep-performance.json"
    alerts = argv[4] if len(argv) > 4 else "/tmp/pt-deep-alerts.json"

    all_findings: list[str] = []
    for path, fn in (
        (overview, audit_overview),
        (holdings, audit_holdings),
        (alerts, audit_alerts),
    ):
        if not Path(path).exists():
            all_findings.append(f"missing file {path}")
            continue
        all_findings.extend(fn(path))
    if Path(performance).exists() and Path(overview).exists():
        all_findings.extend(audit_performance(performance, overview))
    existing = [p for p in (overview, holdings, performance, alerts) if Path(p).exists()]
    all_findings.extend(audit_secrets(*existing))

    if not all_findings:
        print("OK — no invariant violations")
        return 0
    for item in all_findings:
        finding("INV", item)
    print(f"{len(all_findings)} finding(s)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 3: Write deep_smoke.sh**

Create `scripts/deep_smoke.sh`:

```bash
#!/usr/bin/env bash
# Adversarial + full-data deep smoke. Requires API already running.
# Phase A (empty/edge) expects a fresh or low-data DB for empty-state checks —
# run Phase A before OAuth/import, or pass PHASE=full to skip empty asserts.
set -euo pipefail
BASE="${BASE_URL:-http://127.0.0.1:8000}"
DL="${DOWNLOADS_DIR:-$HOME/Downloads}"
PHASE="${PHASE:-all}"  # all | empty | full | audit
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

EQUITY_CSVS=(
  "${DL}/tradebook-RYY010-EQ (2).csv"
  "${DL}/tradebook-RYY010-EQ (1).csv"
  "${DL}/tradebook-RYY010-EQ.csv"
)
MF_CSVS=(
  "${DL}/tradebook-RYY010-MF.csv"
  "${DL}/tradebook-RYY010-MF (1).csv"
  "${DL}/tradebook-RYY010-MF (2).csv"
)

run_empty() {
  echo "== empty /health =="
  curl -sf "$BASE/health" | tee /tmp/pt-deep-health.json
  grep -q '"status":"ok"' /tmp/pt-deep-health.json

  echo "== empty portfolio surfaces =="
  curl -sf "$BASE/portfolio/overview" | tee /tmp/pt-deep-empty-overview.json
  curl -sf "$BASE/portfolio/holdings" | tee /tmp/pt-deep-empty-holdings.json
  curl -sf "$BASE/portfolio/alerts" | tee /tmp/pt-deep-empty-alerts.json
  curl -sf "$BASE/portfolio/performance" | tee /tmp/pt-deep-empty-performance.json
  python3 - <<'PY'
import json
ov = json.load(open("/tmp/pt-deep-empty-overview.json"))
h = json.load(open("/tmp/pt-deep-empty-holdings.json"))
assert ov.get("total_value") in (0, 0.0), ov
assert h.get("holdings") == [], h
print("empty portfolio OK")
PY

  echo "== import no files =="
  code=$(curl -s -o /tmp/pt-deep-import-none.json -w "%{http_code}" -X POST "$BASE/import/csv")
  test "$code" = "400"
  python3 - <<'PY'
import json
body = json.load(open("/tmp/pt-deep-import-none.json"))
detail = body.get("detail") or body
assert "action" in detail or (isinstance(detail, dict) and detail.get("action")), body
print("no-file import OK", detail.get("action", "")[:60] if isinstance(detail, dict) else "")
PY

  echo "== import garbage bytes =="
  printf '\xff\xfe\x00not,csv\n' > /tmp/pt-deep-garbage.bin
  code=$(curl -s -o /tmp/pt-deep-import-garbage.json -w "%{http_code}" \
    -X POST "$BASE/import/csv" -F "file=@/tmp/pt-deep-garbage.bin;type=text/csv")
  test "$code" = "400"
  echo "garbage import HTTP $code"

  echo "== auth callback missing token =="
  code=$(curl -s -o /tmp/pt-deep-cb-missing.json -w "%{http_code}" \
    "$BASE/auth/callback?status=success")
  test "$code" = "400" || test "$code" = "422" || test "$code" = "401"
  echo "missing token HTTP $code"

  echo "== auth callback status=error =="
  code=$(curl -s -o /tmp/pt-deep-cb-error.json -w "%{http_code}" \
    "$BASE/auth/callback?status=error&request_token=fake")
  test "$code" != "200"
  echo "status=error HTTP $code"

  echo "== sync without auth =="
  code=$(curl -s -o /tmp/pt-deep-sync-unauth.json -w "%{http_code}" -X POST "$BASE/sync")
  test "$code" = "401"
  echo "unauth sync HTTP $code"
}

run_full() {
  echo "== multi-file import =="
  FORM_ARGS=()
  for f in "${EQUITY_CSVS[@]}" "${MF_CSVS[@]}"; do
    test -f "$f" || { echo "MISSING: $f"; exit 1; }
    FORM_ARGS+=(-F "files=@${f};type=text/csv")
  done
  if [[ -n "${EQ_FRESH_CSV:-}" && -f "${EQ_FRESH_CSV}" ]]; then
    FORM_ARGS+=(-F "files=@${EQ_FRESH_CSV};type=text/csv")
  fi
  if [[ -n "${MF_FRESH_CSV:-}" && -f "${MF_FRESH_CSV}" ]]; then
    FORM_ARGS+=(-F "files=@${MF_FRESH_CSV};type=text/csv")
  fi
  curl -sf -X POST "$BASE/import/csv" "${FORM_ARGS[@]}" | tee /tmp/pt-deep-import.json

  echo "== equity-only re-batch (idempotent) =="
  EQ_ARGS=()
  for f in "${EQUITY_CSVS[@]}"; do EQ_ARGS+=(-F "files=@${f};type=text/csv"); done
  curl -sf -X POST "$BASE/import/csv" "${EQ_ARGS[@]}" | tee /tmp/pt-deep-import-eq-only.json
  python3 - <<'PY'
import json
body = json.load(open("/tmp/pt-deep-import-eq-only.json"))
assert body["summary"]["new"] == 0, body["summary"]
print("equity-only idempotent OK")
PY

  echo "== sync #1 =="
  curl -sf -X POST "$BASE/sync" | tee /tmp/pt-deep-sync1.json
  echo "== sync #2 (idempotent holdings) =="
  curl -sf -X POST "$BASE/sync" | tee /tmp/pt-deep-sync2.json
  python3 - <<'PY'
import json
a = json.load(open("/tmp/pt-deep-sync1.json"))
b = json.load(open("/tmp/pt-deep-sync2.json"))
assert a.get("holdings_count") == b.get("holdings_count"), (a, b)
print("double sync holdings_count stable", a.get("holdings_count"))
PY

  echo "== portfolio dumps =="
  curl -sf "$BASE/portfolio/overview" | tee /tmp/pt-deep-overview.json
  curl -sf "$BASE/portfolio/holdings" | tee /tmp/pt-deep-holdings.json
  curl -sf "$BASE/portfolio/alerts" | tee /tmp/pt-deep-alerts.json
  curl -sf "$BASE/portfolio/performance" | tee /tmp/pt-deep-performance.json
  curl -sf "$BASE/settings/benchmarks" | tee /tmp/pt-deep-benchmarks.json
}

run_audit() {
  python3 "$ROOT/scripts/audit_portfolio_invariants.py" \
    /tmp/pt-deep-overview.json \
    /tmp/pt-deep-holdings.json \
    /tmp/pt-deep-performance.json \
    /tmp/pt-deep-alerts.json
}

case "$PHASE" in
  empty) run_empty ;;
  full) run_full ;;
  audit) run_audit ;;
  all)
    run_empty
    echo "NOTE: complete OAuth in browser, then: PHASE=full $0 && PHASE=audit $0"
    ;;
  *) echo "Unknown PHASE=$PHASE"; exit 2 ;;
esac

echo "deep_smoke PHASE=$PHASE done"
```

Make executable:

```bash
chmod +x scripts/deep_smoke.sh scripts/audit_portfolio_invariants.py
```

- [ ] **Step 4: Write checklist doc**

Create `docs/superpowers/manual/2026-08-01-deep-smoke-checklist.md` with exactly this body:

```markdown
# Deep API smoke checklist — 2026-08-01

Adversarial pass after first live smoke (`2026-08-01-live-findings.md`).
On auditor `FINDING` or unexpected HTTP → append a bugs row in
`2026-08-01-deep-findings.md`. Do not invent fixes mid-run unless blocking (500/crash).

**Prime hypothesis:** first smoke saw `ITD` + `3Y` with `1Y` null. Spec nesting
requires `1Y` if `3Y` is calendar-eligible. Code nulls the whole portfolio window
when any instrument lacks an opening price — confirm with
`scripts/audit_portfolio_invariants.py` + the UNPRICED_AT_1Y SQL snippet in the plan.

## 0. Prerequisites
- [ ] `.env` keys present; redirect `http://127.0.0.1:8000/auth/callback`
- [ ] Six locked FY CSV slices present under `$HOME/Downloads`
- [ ] Optional: fresh EQ/MF slices → export `EQ_FRESH_CSV` / `MF_FRESH_CSV`

## 1. Fresh DB
```bash
rm -f data/portfolio.db && npm run api
curl -sf http://127.0.0.1:8000/health
```

## 2. Empty + edge (`PHASE=empty`)
```bash
PHASE=empty ./scripts/deep_smoke.sh
```
- [ ] Empty overview/holdings OK
- [ ] No-file import 400 + action
- [ ] Garbage import 400
- [ ] Callback missing token 4xx
- [ ] Callback status=error not 200
- [ ] Sync unauth 401

## 3. Auth edges
- [ ] Login → GET callback → status connected
- [ ] Reused request_token → 4xx, no secrets in body

## 4. Import edges
- [ ] Header-only empty CSV → 200 new=0 or 400+action (not 500)
- [ ] MF-only single file accepted

## 5. Full data + invariants
```bash
PHASE=full ./scripts/deep_smoke.sh
PHASE=audit ./scripts/deep_smoke.sh; echo exit=$?
```
- [ ] Double sync holdings_count stable
- [ ] Auditor exit 0 **or** each FINDING filed as bug
- [ ] If W1: run UNPRICED_AT_1Y diagnosis from plan Task 3 Step 3
- [ ] Settings benchmark override changes excess (or filed SET1)
- [ ] Gap vs reconcile classified (G1 / R1 / data gap)
- [ ] Residual failed symbols / kite-only MF names noted (P3 unless new liquid fail)

## 6. Optional fresh CSV
- [ ] Import fresh slices → reconcile drops or R1 filed
- [ ] Re-run auditor

## 7. Triage
- [ ] Fill deep-findings Verdict
- [ ] Create `docs/superpowers/plans/2026-08-01-api-deep-fixes.md` if any P0/P1
```

- [ ] **Step 5: Dry-run auditor against prior smoke dumps if present**

```bash
# If /tmp/pt-overview.json etc. still exist from first smoke:
python3 scripts/audit_portfolio_invariants.py \
  /tmp/pt-overview.json /tmp/pt-holdings.json \
  /tmp/pt-performance.json /tmp/pt-alerts.json || true
```

Expected: either `OK` or printed `FINDING INV: … 3Y present but 1Y null …` (pre-confirms hypothesis without a new DB). Record any pre-findings in deep-findings as `PRE-*` with status `to-confirm`.

- [ ] **Step 6: Commit docs + scripts only**

```bash
git add docs/superpowers/manual/2026-08-01-deep-smoke-checklist.md \
  docs/superpowers/manual/2026-08-01-deep-findings.md \
  scripts/deep_smoke.sh \
  scripts/audit_portfolio_invariants.py
git commit -m "$(cat <<'EOF'
docs: add deep API bug-hunt checklist and invariant auditor

EOF
)"
```

---

### Task 2: Empty-state + auth/import edge pass (fresh DB)

**Files:**
- Modify (local only): `data/portfolio.db` — never commit
- Modify: `docs/superpowers/manual/2026-08-01-deep-findings.md`

**Interfaces:**
- Consumes: Task 1 scripts; running API on `:8000`
- Produces: filled empty/auth/import checklist rows + any `E-*` / `A-*` / `I-*` bug IDs

- [ ] **Step 1: Fresh DB + start API**

```bash
mkdir -p data
rm -f data/portfolio.db
npm run api
```

Other terminal:

```bash
curl -sf http://127.0.0.1:8000/health
PHASE=empty ./scripts/deep_smoke.sh
```

Expected:
- Empty overview `total_value == 0`, holdings `[]`
- No-file import → 400 with `action`
- Garbage file → 400
- Callback missing token → 4xx
- Callback `status=error` → not 200
- Sync without auth → 401
- No process crash / 500

On any 500 or crash → bug `E1` P0.

- [ ] **Step 2: Auth edges (interactive)**

```bash
curl -sf http://127.0.0.1:8000/auth/login-url | tee /tmp/pt-deep-login.json
# Open login_url; complete login once
curl -sf http://127.0.0.1:8000/auth/status | tee /tmp/pt-deep-auth-ok.json
```

Then:

```bash
# Reuse old request_token from browser URL if still visible — expect failure, not 500
curl -s -o /tmp/pt-deep-cb-reuse.json -w "%{http_code}" \
  -X POST http://127.0.0.1:8000/auth/callback \
  -H 'Content-Type: application/json' \
  -d '{"request_token":"PASTE_USED_TOKEN"}'
```

Expected: 4xx; body must not contain `api_secret` or access token string. Log `A-*` if 500 or secret leak.

```bash
python3 - <<'PY'
from pathlib import Path
text = Path("/tmp/pt-deep-cb-reuse.json").read_text().lower()
assert "api_secret" not in text
assert "access_token" not in text
print("no secrets in reuse callback body")
PY
```

- [ ] **Step 3: Import edges on connected DB (before full history)**

```bash
# Empty CSV
printf 'symbol,isin,trade_date,exchange,segment,series,trade_type,auction,quantity,price,trade_id,order_id,order_execution_time\n' \
  > /tmp/pt-deep-empty.csv
curl -s -o /tmp/pt-deep-import-empty.csv.json -w "%{http_code}" \
  -X POST http://127.0.0.1:8000/import/csv \
  -F "file=@/tmp/pt-deep-empty.csv;type=text/csv"
```

Expected: 200 with `new=0` **or** clear 400 with `action` — either is OK if documented; 500 is `I1` P0.

```bash
# MF-only single file
curl -sf -X POST http://127.0.0.1:8000/import/csv \
  -F "file=@$HOME/Downloads/tradebook-RYY010-MF.csv;type=text/csv" \
  | tee /tmp/pt-deep-import-mf-only.json
```

Expected: accepted; `financial_years` present; no equity instruments required.

- [ ] **Step 4: Update findings checklist boxes for empty/auth/import; commit scrubbed notes**

```bash
git add docs/superpowers/manual/2026-08-01-deep-findings.md
git commit -m "$(cat <<'EOF'
docs: record deep smoke empty/auth/import edge results

EOF
)"
```

---

### Task 3: Full-data invariant audit (the bug magnet)

**Files:**
- Modify (local): `data/portfolio.db`
- Modify: `docs/superpowers/manual/2026-08-01-deep-findings.md`
- Read: `/tmp/pt-deep-*.json`

**Interfaces:**
- Consumes: OAuth session from Task 2; locked CSVs; optional `$EQ_FRESH_CSV` / `$MF_FRESH_CSV`
- Produces: auditor exit code + bug rows `W-*` (windows), `M-*` (metrics), `G-*` (gap), `P-*` (prices)

- [ ] **Step 1: Full import + double sync**

```bash
PHASE=full ./scripts/deep_smoke.sh
```

Expected: import accepted; second sync same `holdings_count`; prices `failed` list only for known residual symbols (SGB/delisted/DVR) unless new failures appear.

- [ ] **Step 2: Run invariant auditor**

```bash
PHASE=audit ./scripts/deep_smoke.sh; echo exit=$?
```

**Critical expected hypothesis check:**

| Check | If fails → |
|-------|------------|
| `3Y present but 1Y null` | File **W1** P1 — portfolio window nulls when any opening price missing; confirm which symbols lack price at `as_of-365d` |
| rates look like percent | **M1** P0/P1 |
| allocation weights ≠ 1 | **M2** P1 |
| dust qty | **M3** P2 (F6 regression) |
| gap null + large reconcile | **G1** P1/P2 — gap ignores CSV coverage hole after sync |
| secrets | **S1** P0 |

- [ ] **Step 3: Diagnose W1 if raised (read-only SQL / python)**

```bash
cd apps/api && uv run python - <<'PY'
from datetime import date, timedelta
from portfolio_tracker.db.engine import get_session_factory
from portfolio_tracker.db.models import Instrument, Transaction, Price
from portfolio_tracker.modules.portfolio import _instrument_price_symbol, _qty_at, _transactions

as_of = date.today()
start_1y = (as_of - timedelta(days=365)).isoformat()
start_3y = (as_of - timedelta(days=1095)).isoformat()
Session = get_session_factory()
with Session() as session:
    for inst in session.query(Instrument).all():
        txs = _transactions(session, inst.id, as_of.isoformat())
        q1 = _qty_at(txs, start_1y)
        q3 = _qty_at(txs, start_3y)
        sym = _instrument_price_symbol(inst)
        p1 = session.query(Price).filter(Price.symbol == sym, Price.price_date <= start_1y).order_by(Price.price_date.desc()).first()
        p3 = session.query(Price).filter(Price.symbol == sym, Price.price_date <= start_3y).order_by(Price.price_date.desc()).first()
        if q1 > 0 and p1 is None:
            print("UNPRICED_AT_1Y", inst.symbol, sym, "qty", q1, "3y_qty", q3, "p3", getattr(p3, "price_date", None))
PY
```

Expected for W1 confirmation: ≥1 `UNPRICED_AT_1Y` line. Paste scrubbed symbol list into findings (no quantities if sensitive — symbols OK).

- [ ] **Step 4: Settings excess delta**

```bash
# Pick a valued equity instrument_id from benchmarks dump
ID=$(python3 - <<'PY'
import json
payload = json.load(open("/tmp/pt-deep-benchmarks.json"))
rows = payload if isinstance(payload, list) else payload.get("benchmarks") or payload.get("items") or []
row = next(r for r in rows if r.get("instrument_type") != "mf")
open("/tmp/pt-deep-bench-target.json", "w").write(json.dumps(row, indent=2))
print(row["instrument_id"])
PY
)

curl -sf http://127.0.0.1:8000/portfolio/holdings | tee /tmp/pt-deep-holdings-before-bench.json
curl -sf -X PUT "http://127.0.0.1:8000/settings/benchmarks/${ID}" \
  -H 'Content-Type: application/json' \
  -d '{"benchmark_index":"Nifty Midcap 150"}'
curl -sf http://127.0.0.1:8000/portfolio/holdings | tee /tmp/pt-deep-holdings-after-bench.json
python3 - <<'PY'
import json
target = json.load(open("/tmp/pt-deep-bench-target.json"))
iid = target["instrument_id"]
before = {r["instrument_id"]: r for r in json.load(open("/tmp/pt-deep-holdings-before-bench.json"))["holdings"]}
after = {r["instrument_id"]: r for r in json.load(open("/tmp/pt-deep-holdings-after-bench.json"))["holdings"]}
b, a = before[iid], after[iid]
print("before excess", b.get("absolute_excess_pp"), "bench", b.get("benchmark_index") or b.get("benchmark"))
print("after excess", a.get("absolute_excess_pp"), "bench", a.get("benchmark_index") or a.get("benchmark"))
if (
    b.get("absolute_excess_pp") == a.get("absolute_excess_pp")
    and b.get("absolute_excess_pp") is not None
):
    print("FINDING SET1: benchmark override did not change absolute_excess_pp")
else:
    print("settings excess delta OK or excess null")
PY
```

If override stores `source=user` but excess unchanged when both benches have prices → **SET1** P1.

Restore default if desired:

```bash
curl -sf -X PUT "http://127.0.0.1:8000/settings/benchmarks/${ID}" \
  -H 'Content-Type: application/json' \
  -d '{"benchmark_index":"Nifty 500"}'
```

- [ ] **Step 5: Gap vs reconcile semantics**

```bash
python3 - <<'PY'
import json
alerts = json.load(open("/tmp/pt-deep-alerts.json"))
print("gap", alerts.get("gap"))
print("reconcile_count", len(alerts.get("reconcile") or []))
print("reconcile_message", (alerts.get("reconcile_message") or "")[:120])
PY
```

| Observation | Classification |
|-------------|----------------|
| Fresh CSVs imported through today + reconcile still large | **R1** P1 false positives |
| No fresh CSVs + reconcile large + gap null | **G1** candidate (document; severity P1 if product expects gap from CSV hole) |
| No fresh CSVs + reconcile large + gap suggests last CSV end → today | OK / data gap |

- [ ] **Step 6: Residual price / identity notes (not auto-bugs)**

```bash
python3 - <<'PY'
import json
sync = json.load(open("/tmp/pt-deep-sync2.json"))
failed = (sync.get("prices") or {}).get("failed") or sync.get("failed") or []
print("failed_count", len(failed))
for row in failed:
    print("FAIL", row)
holdings = json.load(open("/tmp/pt-deep-holdings.json"))["holdings"]
for h in holdings:
    sym = h.get("symbol") or ""
    if sym.startswith("INF") and len(sym) >= 12:
        print("KITE_ONLY_MF_NAME", sym, "qty", h.get("qty"), "ltp", h.get("ltp"))
PY
```

File as P3 unless a liquid name newly appears in `failed` (then **P1** rename alias).

- [ ] **Step 7: Commit scrubbed deep findings for this task**

```bash
git add docs/superpowers/manual/2026-08-01-deep-findings.md
git commit -m "$(cat <<'EOF'
docs: record deep API invariant audit findings

EOF
)"
```

---

### Task 4 (optional high-value): Fresh CSV reconcile tightening

**Files:**
- Local only: new Console exports; `data/portfolio.db`
- Modify: `docs/superpowers/manual/2026-08-01-deep-findings.md`

**Interfaces:**
- Consumes: engineer-exported `$EQ_FRESH_CSV` + `$MF_FRESH_CSV`
- Produces: before/after reconcile counts; upgrades G1/R1 severity clarity

Skip this task if fresh exports unavailable — note `skipped` in findings.

- [ ] **Step 1: Export from Console**

- Equity tradebook: **2026-01-23 → today** (≤365 days)
- MF tradebook: **2026-03-06 → today**
- Save under Downloads; set:

```bash
export EQ_FRESH_CSV="$HOME/Downloads/tradebook-RYY010-EQ-fresh.csv"
export MF_FRESH_CSV="$HOME/Downloads/tradebook-RYY010-MF-fresh.csv"
```

(Exact basenames may differ — point env vars at real paths.)

- [ ] **Step 2: Import fresh slices only + sync + re-audit**

```bash
curl -sf -X POST http://127.0.0.1:8000/import/csv \
  -F "files=@${EQ_FRESH_CSV};type=text/csv" \
  -F "files=@${MF_FRESH_CSV};type=text/csv" \
  | tee /tmp/pt-deep-import-fresh.json
curl -sf -X POST http://127.0.0.1:8000/sync | tee /tmp/pt-deep-sync-fresh.json
curl -sf http://127.0.0.1:8000/portfolio/alerts | tee /tmp/pt-deep-alerts-fresh.json
curl -sf http://127.0.0.1:8000/portfolio/overview | tee /tmp/pt-deep-overview.json
curl -sf http://127.0.0.1:8000/portfolio/holdings | tee /tmp/pt-deep-holdings.json
curl -sf http://127.0.0.1:8000/portfolio/performance | tee /tmp/pt-deep-performance.json
PHASE=audit ./scripts/deep_smoke.sh || true
python3 - <<'PY'
import json
a = json.load(open("/tmp/pt-deep-alerts-fresh.json"))
print("reconcile_after_fresh", len(a.get("reconcile") or []))
print("gap_after_fresh", a.get("gap"))
PY
```

Expected: reconcile count drops sharply vs Task 3. Remaining diffs → **R1** P1 with symbol list. Re-check W1 after more price history days exist.

- [ ] **Step 3: Commit findings update**

```bash
git add docs/superpowers/manual/2026-08-01-deep-findings.md
git commit -m "$(cat <<'EOF'
docs: record deep smoke results after fresh CSV backfill

EOF
)"
```

---

### Task 5: Triage → deep-fixes plan

**Files:**
- Modify: `docs/superpowers/manual/2026-08-01-deep-findings.md`
- Create (only if ≥1 P0/P1): `docs/superpowers/plans/2026-08-01-api-deep-fixes.md`

**Interfaces:**
- Consumes: bugs table from Tasks 2–4
- Produces: ordered TDD fix tasks **or** verdict that API remains frontend-ready

- [ ] **Step 1: Classify each finding**

| Severity | Meaning | Action |
|----------|---------|--------|
| P0 | Crash, 500, secret leak, metrics off by 100× | Fix before frontend |
| P1 | Wrong windows/numbers, false reconcile, settings no-op, gap lies | Fix before frontend |
| P2 | Polish / incomplete flags / kite-only display names | Fix if cheap |
| P3 | Known data (SGB, delisted, missing fresh CSV) | Document only |

Likely W1 fix direction (for the fixes plan — do **not** implement in this task): when building portfolio rolling windows, skip or mark incomplete for instruments missing opening price instead of nulling the entire window; surface which symbols blocked the window. Confirm against design §7 "Price/benchmark fetch fail → metrics marked incomplete".

Likely G1 fix direction: gap detection should consider `max(transaction.trade_date)` as well as `last_trade_append_at`, or sync should not advance append watermark when `trades_appended=0` and CSV hole remains — product choice; capture in fix task after triage interview if ambiguous.

- [ ] **Step 2: Draft fix tasks with full TDD bodies**

Each fix in `2026-08-01-api-deep-fixes.md`:

```markdown
### Fix N: [short title]

**Files:**
- Modify: `exact/path`
- Test: `exact/path`

**Failing behavior:** …
**Repro:** …

- [ ] Step 1: failing test (full code)
- [ ] Step 2: run — expect FAIL
- [ ] Step 3: minimal fix (full code)
- [ ] Step 4: PASS + full suite
- [ ] Step 5: commit
- [ ] Step 6: re-run the single deep curl / auditor check
```

- [ ] **Step 3: If zero P0/P1**

Write: `Verdict: Deep pass clean — API still ready for Task 12 frontend.` Do not create an empty fixes plan.

- [ ] **Step 4: Commit triage**

```bash
git add docs/superpowers/manual/2026-08-01-deep-findings.md
# and fixes plan if created
git commit -m "$(cat <<'EOF'
docs: triage deep API bug-hunt findings

EOF
)"
```

---

### Task 6: Execute deep fixes (gate)

**Files:** whatever Task 5 lists

**Interfaces:**
- Consumes: `2026-08-01-api-deep-fixes.md`
- Produces: green tests + auditor exit 0 on re-run (or documented accepted P3 residuals)

- [ ] **Step 1: Implement fixes P0 → P1 → cheap P2** using TDD per fix task

- [ ] **Step 2: Re-run deep pass**

```bash
rm -f data/portfolio.db
npm run api
# OAuth once
PHASE=empty ./scripts/deep_smoke.sh
# OAuth if wiped
PHASE=full ./scripts/deep_smoke.sh
PHASE=audit ./scripts/deep_smoke.sh
```

Expected: auditor exit 0, or only documented P3 residuals.

- [ ] **Step 3: Final verdict commit**

Update findings `Verdict:` line. Commit docs only.

---

## Self-Review

**1. Spec coverage:** Design §6 first-run edges, §7 error matrix (empty, bad CSV, expired/missing token, price fail → incomplete, gap, reconcile), §8 manual tests, locked window/excess/rate rules. First smoke covered happy path; this plan covers contradictions and edges. Frontend still blocked only on new P0/P1.

**2. Placeholder scan:** No TBD. Task 6 depends on Task 5 output by design. Fix template requires full code when written. W1/G1 fix directions noted as triage guidance, not silent "implement later" without a task.

**3. Type consistency:** Auditor paths match `deep_smoke.sh` outputs; portfolio shapes match `get_overview` / `get_holdings` / `get_performance` / `get_alerts`; import error `action` matches `csv_import.REIMPORT_ACTION` pattern from first smoke.

**Known risks:**
- Weekend: `trades_appended` may be 0 — not a bug
- W1 may be intentional "all or nothing window" — still file; product may choose incomplete-partial vs null
- Fresh CSVs optional; without them reconcile noise stays high
- Do not re-open fixed F1–F7 unless regression

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-01-api-deep-bug-hunt.md`. Two execution options:

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
