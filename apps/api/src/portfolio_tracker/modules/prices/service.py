from __future__ import annotations

from datetime import date
from typing import TypedDict

from sqlalchemy import func
from sqlalchemy.orm import Session

from portfolio_tracker.db.models import BenchmarkPrice, Instrument, Price
from portfolio_tracker.modules.prices.amfi import AmfiNavProvider
from portfolio_tracker.modules.prices.yahoo import INDEX_TICKERS, YahooFinanceProvider


class PriceRefreshResult(TypedDict):
    updated: int
    failed: list[str]
    incomplete: bool


def _latest_price_date(
    session: Session, model: type[Price] | type[BenchmarkPrice], symbol_field, symbol: str
) -> str | None:
    date_column = model.price_date
    return session.query(func.max(date_column)).filter(symbol_field == symbol).scalar()


def _upsert_price(
    session: Session, symbol: str, price_date: str, close: float, source: str
) -> None:
    row = (
        session.query(Price)
        .filter(Price.symbol == symbol, Price.price_date == price_date)
        .first()
    )
    if row is None:
        session.add(
            Price(
                symbol=symbol,
                price_date=price_date,
                close=close,
                source=source,
            )
        )
        session.flush()
        return
    row.close = close
    row.source = source


def _upsert_benchmark(
    session: Session, index_symbol: str, price_date: str, close: float
) -> None:
    row = (
        session.query(BenchmarkPrice)
        .filter(
            BenchmarkPrice.index_symbol == index_symbol,
            BenchmarkPrice.price_date == price_date,
        )
        .first()
    )
    if row is None:
        session.add(
            BenchmarkPrice(
                index_symbol=index_symbol,
                price_date=price_date,
                close=close,
            )
        )
        session.flush()
        return
    row.close = close


def _history_start_for_price(
    session: Session, symbol: str, history_start: str
) -> str:
    return (
        _latest_price_date(session, Price, Price.symbol, symbol) or history_start
    )


def _refresh_mutual_fund(
    session: Session,
    instrument: Instrument,
    amfi: AmfiNavProvider,
    history_start: str,
    as_of: str,
) -> int:
    isin = instrument.isin or instrument.symbol
    start = _history_start_for_price(session, isin, history_start)
    history = amfi.get_history_by_isin(isin, start, as_of)
    for price_date, close in history:
        _upsert_price(session, isin, price_date, close, "amfi")

    category, scheme_code = amfi.resolve_category(isin)
    if scheme_code:
        instrument.scheme_code = scheme_code
    if category and instrument.mf_category_source != "user":
        instrument.mf_category = category
        instrument.mf_category_source = "amfi"
        instrument.needs_category = 0
    elif not instrument.mf_category:
        instrument.needs_category = 1
    return len(history)


def _equity_candidates(instrument: Instrument) -> list[str]:
    if instrument.yahoo_symbol:
        return [instrument.yahoo_symbol]
    return [f"{instrument.symbol}.NS", f"{instrument.symbol}.BO"]


def _fetch_equity_prices(
    session: Session,
    instrument: Instrument,
    yahoo: YahooFinanceProvider,
    history_start: str,
    as_of: str,
) -> tuple[str, list[tuple[str, float]], float]:
    for candidate in _equity_candidates(instrument):
        start = _history_start_for_price(session, candidate, history_start)
        history = yahoo.get_history(candidate, start, as_of)
        if not history:
            continue
        ltp = yahoo.get_ltp(candidate)
        if ltp is not None:
            return candidate, history, ltp
    raise RuntimeError("no Yahoo history and LTP for available symbol")


def _refresh_equity(
    session: Session,
    instrument: Instrument,
    yahoo: YahooFinanceProvider,
    history_start: str,
    as_of: str,
) -> int:
    symbol, history, ltp = _fetch_equity_prices(
        session, instrument, yahoo, history_start, as_of
    )
    instrument.yahoo_symbol = symbol
    for price_date, close in history:
        _upsert_price(session, symbol, price_date, close, "yahoo")
    _upsert_price(session, symbol, as_of, ltp, "yahoo")
    return len(history) + 1


def _refresh_benchmarks(
    session: Session,
    yahoo: YahooFinanceProvider,
    names: list[str],
    history_start: str,
    as_of: str,
    failed: list[str],
) -> int:
    updated = 0
    for name in names:
        try:
            start = (
                _latest_price_date(
                    session,
                    BenchmarkPrice,
                    BenchmarkPrice.index_symbol,
                    name,
                )
                or history_start
            )
            history = yahoo.get_history(INDEX_TICKERS[name], start, as_of)
            for price_date, close in history:
                _upsert_benchmark(session, name, price_date, close)
            updated += len(history)
        except Exception as error:
            failed.append(f"benchmark {name}: {error}")
    return updated


def refresh_prices(
    session: Session,
    *,
    as_of: str | None = None,
    history_start: str = "2018-01-01",
    yahoo: YahooFinanceProvider | None = None,
    amfi: AmfiNavProvider | None = None,
    benchmark_names: list[str] | None = None,
) -> PriceRefreshResult:
    yahoo_provider = yahoo or YahooFinanceProvider()
    amfi_provider = amfi or AmfiNavProvider()
    refresh_date = as_of or date.today().isoformat()
    failed: list[str] = []
    updated = 0

    for instrument in session.query(Instrument).all():
        try:
            if instrument.instrument_type == "mf":
                updated += _refresh_mutual_fund(
                    session, instrument, amfi_provider, history_start, refresh_date
                )
            else:
                updated += _refresh_equity(
                    session, instrument, yahoo_provider, history_start, refresh_date
                )
        except Exception as error:
            failed.append(f"{instrument.symbol}: {error}")

    names = list(INDEX_TICKERS) if benchmark_names is None else benchmark_names
    updated += _refresh_benchmarks(
        session, yahoo_provider, names, history_start, refresh_date, failed
    )
    return {"updated": updated, "failed": failed, "incomplete": bool(failed)}
