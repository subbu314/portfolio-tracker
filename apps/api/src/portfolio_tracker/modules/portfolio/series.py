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
