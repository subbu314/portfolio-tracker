# API Live Fixes — 2026-08-01

From `docs/superpowers/manual/2026-08-01-live-findings.md`. Order: P0 → P1 → cheap P2.

| ID | Severity | Verdict |
|----|----------|---------|
| F2 | P0 | Fix — Kite MF identity split |
| F1 | P0 | Fix — silent AMFI empty history |
| F3 | P1 | Fix — Yahoo rename aliases; SGB stay failed/P3 |
| F4 | — | Not a bug — contributors sorted by `absolute_excess_pp` (design: contributor excess) |
| F5 | P2 | Deferred — follows from F1/F2; re-check after second live pass |
| F6 | P2 | Fix if cheap — near-zero qty flatten |
| F7 | P3 | Done (`268fb1c`) |
| F8 | P3 | Data gap — document only |

---

### Fix 1: Merge Kite MF holdings onto CSV instruments by ISIN (F2)

**Files:**
- Modify: `apps/api/src/portfolio_tracker/modules/kite_sync.py`
- Modify: `apps/api/src/portfolio_tracker/modules/csv_import.py` (`get_or_create_instrument`)
- Test: `apps/api/tests/test_kite_sync.py`

**Failing behavior:** Kite `mf_holdings` often has `tradingsymbol=<ISIN>` and omits `isin`. Sync creates a second instrument; snapshot qty and CSV txs diverge.

- [ ] Step 1: failing test (full code)

```python
def test_mf_sync_merges_kite_isin_tradingsymbol_onto_csv_instrument():
    Session = get_session_factory()
    with Session() as session:
        session.add(Setting(key=kite_auth.TOKEN_KEY, value="token"))
        named = Instrument(
            symbol="QUANT SMALL CAP FUND - DIRECT PLAN",
            isin="INF966L01689",
            instrument_type="mf",
            exchange="BSE",
        )
        session.add(named)
        session.commit()
        named_id = named.id

        kite = MagicMock()
        kite.holdings.return_value = []
        kite.mf_holdings.return_value = [
            {
                "tradingsymbol": "INF966L01689",
                # live Kite omits isin
                "quantity": 1234.977,
                "average_price": 257.96,
            }
        ]
        kite.trades.return_value = []

        with (
            patch.object(kite_auth, "authenticated_kite", return_value=kite),
            patch.object(kite_sync, "_today_ist", return_value="2026-08-01"),
        ):
            result = kite_sync.sync_all(session)
        session.commit()

        assert result["holdings_count"] == 1
        assert session.query(Instrument).filter(Instrument.instrument_type == "mf").count() == 1
        merged = session.query(Instrument).one()
        assert merged.id == named_id
        assert merged.symbol == "QUANT SMALL CAP FUND - DIRECT PLAN"
        assert merged.isin == "INF966L01689"
        snap = session.query(HoldingsSnapshot).one()
        assert snap.instrument_id == named_id
        assert snap.quantity == 1234.977
```

- [ ] Step 2: run — expect FAIL (second MF instrument created)
- [ ] Step 3: fix — in `_sync_holding`, if MF and `isin` missing but `tradingsymbol` looks like ISIN (`^[A-Z]{2}[A-Z0-9]{9}\d$` or starts with `INF`), set `isin=tradingsymbol`. Prefer existing instrument's fund-name `symbol` when ISIN match exists. In `get_or_create_instrument`, if `isin` null and `symbol` looks like ISIN, look up `Instrument.isin == symbol` and set `isin` on create/match.
- [ ] Step 4: run — expect PASS + full suite
- [ ] Step 5: commit `fix: merge Kite MF ISIN tradingsymbols onto CSV instruments`
- [ ] Step 6: re-run live — after re-auth + import + sync, no duplicate INF* MF instruments; snapshot ids match named funds

---

### Fix 2: Surface empty AMFI history as `prices.failed` (F1)

**Files:**
- Modify: `apps/api/src/portfolio_tracker/modules/prices/service.py`
- Test: `apps/api/tests/test_prices.py`

**Failing behavior:** `get_history_by_isin` returns `[]` → `updated+=0`, not listed in `failed`; MF `ltp` stays null with no signal.

- [ ] Step 1: failing test

```python
def test_refresh_prices_reports_missing_amfi_nav_as_failed():
    Session = get_session_factory()
    with Session() as session:
        session.add(
            Instrument(
                symbol="SOME MF",
                isin="INF000000001",
                instrument_type="mf",
            )
        )
        session.commit()

        amfi = MagicMock()
        amfi.get_history_by_isin.return_value = []
        amfi.resolve_category.return_value = (None, None)
        yahoo = MagicMock()
        yahoo.get_history.return_value = []
        yahoo.get_ltp.return_value = None

        result = refresh_prices(
            session,
            as_of="2026-08-01",
            yahoo=yahoo,
            amfi=amfi,
            benchmark_names=[],
        )

        assert result["updated"] == 0
        assert result["incomplete"] is True
        assert any("INF000000001" in row or "SOME MF" in row for row in result["failed"])
        assert any("AMFI" in row or "amfi" in row.lower() or "NAV" in row for row in result["failed"])
```

- [ ] Step 2: run — expect FAIL
- [ ] Step 3: fix — in `_refresh_mutual_fund`, if `history` empty after fetch, `raise RuntimeError(f"no AMFI NAV for {isin}")`
- [ ] Step 4: PASS + full suite
- [ ] Step 5: commit `fix: report empty AMFI NAV refresh as prices.failed`
- [ ] Step 6: live `/sync` — MF misses appear in `prices.failed` when mfapi fails; when mfapi works, AMFI rows > 0

---

### Fix 3: Yahoo rename aliases for known failed liquid names (F3)

**Files:**
- Modify: `apps/api/src/portfolio_tracker/modules/prices/service.py`
- Test: `apps/api/tests/test_prices.py`

**Failing behavior:** `ZOMATO.NS` etc. fail after rename; sync lists them in `prices.failed`.

Minimal alias map (NSE Yahoo ticker):

| symbol | yahoo |
|--------|-------|
| ZOMATO | ETERNAL.NS |
| TATAMOTORS | TATAMOTORS.NS (try; if demerged keep fail) |
| HBLPOWER | HBLENGINE.NS |
| SWANENERGY | SWANCORP.NS |
| IDFC | (delisted — leave failed) |
| SGB* | unsupported — leave failed (P3) |

- [ ] Step 1: failing test — instrument `ZOMATO` with no yahoo_symbol; mock yahoo succeeds only for `ETERNAL.NS`; expect refresh stores under ETERNAL and sets `yahoo_symbol`
- [ ] Step 2: FAIL
- [ ] Step 3: add `YAHOO_SYMBOL_ALIASES` consulted in `_equity_candidates`
- [ ] Step 4: PASS
- [ ] Step 5: commit `fix: map renamed NSE tickers to current Yahoo symbols`
- [ ] Step 6: live sync — ZOMATO/HBLPOWER/SWANENERGY leave `failed` list when aliases resolve

---

### Fix 4 (P2, cheap): Flatten dust MF quantities (F6)

**Files:**
- Modify: `apps/api/src/portfolio_tracker/modules/portfolio.py` (or kite_sync upsert)
- Test: unit on holdings qty display / snapshot read

- [ ] Step 1–5: treat `|qty| < 1e-8` as `0` when building holdings rows; commit `fix: treat near-zero holding quantities as flat zero`

---

## Second live pass (after fixes)

```bash
rm -f data/portfolio.db
# re-auth, multi-file import, sync, spot-check total_value vs Console ±5%
```

Update findings `Verdict:` line.
