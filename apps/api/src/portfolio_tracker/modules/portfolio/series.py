from __future__ import annotations

from sqlalchemy.orm import Session

from portfolio_tracker.db.models import (
    BenchmarkMap,
    BenchmarkPrice,
    Instrument,
    Price,
    Transaction,
)
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


def _load_price_history(
    session: Session,
    model: type[Price] | type[BenchmarkPrice],
    symbol_column,
    symbols: set[str],
    as_of: str,
) -> dict[str, list[tuple[str, float]]]:
    if not symbols:
        return {}
    rows = (
        session.query(symbol_column, model.price_date, model.close)
        .filter(symbol_column.in_(symbols), model.price_date <= as_of)
        .order_by(symbol_column.asc(), model.price_date.asc())
        .all()
    )
    histories: dict[str, list[tuple[str, float]]] = {}
    for symbol, price_date, close in rows:
        histories.setdefault(symbol, []).append((price_date, close))
    return histories


def _forward_fill_prices(
    histories: dict[str, list[tuple[str, float]]], dates: list[str]
) -> dict[str, dict[str, float | None]]:
    prices_by_day: dict[str, dict[str, float | None]] = {}
    for symbol, history in histories.items():
        next_row = 0
        latest: float | None = None
        for day in dates:
            while next_row < len(history) and history[next_row][0] <= day:
                latest = history[next_row][1]
                next_row += 1
            prices_by_day.setdefault(day, {})[symbol] = latest
    return prices_by_day


def _portfolio_mv_on_day(
    instruments: list[Instrument],
    transactions_by_instrument: dict[int, list[Transaction]],
    prices_by_symbol: dict[str, float | None],
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
        price = prices_by_symbol.get(_instrument_price_symbol(instrument))
        if price is None:
            incomplete = True
            continue
        value = qty * price
        values[instrument.id] = value
        total += value
    return total, values, incomplete


def _portfolio_price_dates(
    price_history: dict[str, list[tuple[str, float]]], start: str, as_of: str
) -> list[str]:
    return sorted(
        {
            start,
            as_of,
            *(
                price_date
                for history in price_history.values()
                for price_date, _close in history
                if price_date >= start
            ),
        }
    )


def _first_complete_base(
    instruments: list[Instrument],
    transactions_by_instrument: dict[int, list[Transaction]],
    prices_by_day: dict[str, dict[str, float | None]],
    candidate_dates: list[str],
) -> tuple[str | None, float, dict[int, float], bool]:
    incomplete = False
    for day in candidate_dates:
        mv, values, day_incomplete = _portfolio_mv_on_day(
            instruments, transactions_by_instrument, prices_by_day.get(day, {}), day
        )
        incomplete = incomplete or day_incomplete
        if mv > 0 and not day_incomplete:
            return day, mv, values, incomplete
    return None, 0.0, {}, incomplete


def _benchmark_by_instrument(
    session: Session, instruments: list[Instrument]
) -> dict[int, str]:
    instrument_ids = [instrument.id for instrument in instruments]
    benchmark_maps = {
        benchmark_map.instrument_id: benchmark_map
        for benchmark_map in session.query(BenchmarkMap)
        .filter(BenchmarkMap.instrument_id.in_(instrument_ids))
        .all()
    }
    benchmark_by_instrument: dict[int, str] = {}
    for instrument in instruments:
        benchmark_map = benchmark_maps.get(instrument.id)
        if benchmark_map is None:
            benchmark_map = BenchmarkMap(
                instrument_id=instrument.id,
                benchmark_index=benchmarks.default_benchmark_for(instrument),
                source="default",
            )
            session.add(benchmark_map)
            if instrument.instrument_type == "mf" and not instrument.mf_category:
                instrument.needs_category = 1
        elif benchmark_map.source != "user":
            benchmark_map.benchmark_index = benchmarks.default_benchmark_for(
                instrument
            )
            benchmark_map.source = "default"
        benchmark_by_instrument[instrument.id] = benchmark_map.benchmark_index
    return benchmark_by_instrument


def _base_benchmark_index(
    base_values: dict[int, float],
    base_mv: float,
    benchmark_by_instrument: dict[int, str],
    benchmark_prices: dict[str, float | None],
) -> tuple[dict[int, tuple[str, float, float]], bool]:
    base_index: dict[int, tuple[str, float, float]] = {}
    incomplete = False
    for instrument_id, value in base_values.items():
        index_name = benchmark_by_instrument[instrument_id]
        level = benchmark_prices.get(index_name)
        if level is None or level <= 0:
            incomplete = True
            continue
        base_index[instrument_id] = (index_name, level, value / base_mv)
    return base_index, incomplete


def _benchmark_return(
    base_index: dict[int, tuple[str, float, float]],
    benchmark_prices: dict[str, float | None],
) -> float | None:
    if not base_index:
        return None
    result = 0.0
    for index_name, base_level, weight in base_index.values():
        level = benchmark_prices.get(index_name)
        if level is None or base_level <= 0:
            return None
        result += weight * (level / base_level - 1.0)
    return result


def _portfolio_points(
    instruments: list[Instrument],
    transactions_by_instrument: dict[int, list[Transaction]],
    prices_by_day: dict[str, dict[str, float | None]],
    benchmark_prices_by_day: dict[str, dict[str, float | None]],
    candidate_dates: list[str],
    base_day: str,
    base_mv: float,
    base_index: dict[int, tuple[str, float, float]],
) -> tuple[list[dict], bool]:
    points: list[dict] = []
    incomplete = False
    for day in (date for date in candidate_dates if date >= base_day):
        mv, _values, day_incomplete = _portfolio_mv_on_day(
            instruments, transactions_by_instrument, prices_by_day.get(day, {}), day
        )
        incomplete = incomplete or day_incomplete
        portfolio_return = (
            mv / base_mv - 1.0 if mv > 0 and not day_incomplete else None
        )
        benchmark_return = _benchmark_return(
            base_index, benchmark_prices_by_day.get(day, {})
        )
        incomplete = incomplete or benchmark_return is None
        points.append(
            {
                "date": day,
                "portfolio_return": portfolio_return,
                "benchmark_return": benchmark_return,
                "holding_return": None,
            }
        )
    return points, incomplete


def get_portfolio_series(session: Session, as_of: str, window: str) -> dict:
    if window not in VALID_WINDOWS:
        raise ValueError(f"Unknown window: {window}")
    inputs = load_portfolio_inputs(session, as_of)
    all_txs = sorted(
        (tx for txs in inputs.transactions_by_instrument.values() for tx in txs),
        key=lambda tx: tx.trade_date,
    )
    if not all_txs:
        return _empty_series(window, as_of)
    start = metrics.window_start(as_of, window, all_txs[0].trade_date)
    if start is None:
        return _empty_series(window, as_of)
    symbols = {
        _instrument_price_symbol(inst)
        for inst in inputs.instruments
        if inputs.transactions_by_instrument.get(inst.id)
    }
    price_history = _load_price_history(
        session, Price, Price.symbol, symbols, as_of
    )
    candidate_dates = _portfolio_price_dates(price_history, start, as_of)
    prices_by_day = _forward_fill_prices(price_history, candidate_dates)
    base_day, base_mv, base_values, incomplete = _first_complete_base(
        inputs.instruments,
        inputs.transactions_by_instrument,
        prices_by_day,
        candidate_dates,
    )
    if base_day is None or base_mv <= 0:
        return _empty_series(window, as_of, start=start)
    benchmark_by_instrument = _benchmark_by_instrument(
        session, inputs.instruments
    )
    benchmark_history = _load_price_history(
        session,
        BenchmarkPrice,
        BenchmarkPrice.index_symbol,
        set(benchmark_by_instrument.values()),
        as_of,
    )
    benchmark_prices_by_day = _forward_fill_prices(
        benchmark_history, candidate_dates
    )
    base_index, base_incomplete = _base_benchmark_index(
        base_values,
        base_mv,
        benchmark_by_instrument,
        benchmark_prices_by_day.get(base_day, {}),
    )
    points, points_incomplete = _portfolio_points(
        inputs.instruments,
        inputs.transactions_by_instrument,
        prices_by_day,
        benchmark_prices_by_day,
        candidate_dates,
        base_day,
        base_mv,
        base_index,
    )
    incomplete = incomplete or base_incomplete or points_incomplete

    return {
        "window": window,
        "metric": "absolute",
        "as_of": as_of,
        "start": start,
        "available": True,
        "incomplete": incomplete,
        "points": points,
    }


def _empty_holding_series(
    instrument_id: int,
    window: str,
    as_of: str,
    benchmark: str,
    *,
    start: str | None = None,
    incomplete: bool = False,
) -> dict:
    return {
        "instrument_id": instrument_id,
        "window": window,
        "metric": "absolute",
        "benchmark": benchmark,
        "as_of": as_of,
        "start": start,
        "available": False,
        "incomplete": incomplete,
        "points": [],
    }


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

    benchmark = benchmarks.ensure_benchmark_map(session, instrument).benchmark_index
    transactions = (
        session.query(Transaction)
        .filter(
            Transaction.instrument_id == instrument_id,
            Transaction.trade_date <= as_of,
        )
        .order_by(Transaction.trade_date.asc())
        .all()
    )
    if not transactions:
        return _empty_holding_series(instrument_id, window, as_of, benchmark)

    start = metrics.window_start(as_of, window, transactions[0].trade_date)
    if start is None:
        return _empty_holding_series(instrument_id, window, as_of, benchmark)

    symbol = _instrument_price_symbol(instrument)
    candidate_dates = _price_dates(session, {symbol}, start, as_of)
    candidate_dates = sorted({*candidate_dates, start, as_of})
    base_day = next(
        (
            day
            for day in candidate_dates
            if (_latest_price(session, symbol, day) or 0) > 0
        ),
        None,
    )
    if base_day is None:
        return _empty_holding_series(
            instrument_id,
            window,
            as_of,
            benchmark,
            start=start,
            incomplete=True,
        )

    base_price = _latest_price(session, symbol, base_day)
    base_benchmark = _benchmark_price(
        session, benchmark, base_day, as_of=as_of
    )
    incomplete = base_benchmark is None or base_benchmark <= 0
    points: list[dict] = []
    for day in (date for date in candidate_dates if date >= base_day):
        price = _latest_price(session, symbol, day)
        benchmark_level = _benchmark_price(
            session, benchmark, day, as_of=as_of
        )
        holding_return = (
            price / base_price - 1.0 if price is not None and base_price else None
        )
        benchmark_return = (
            benchmark_level / base_benchmark - 1.0
            if benchmark_level is not None
            and base_benchmark is not None
            and base_benchmark > 0
            else None
        )
        incomplete = (
            incomplete or holding_return is None or benchmark_return is None
        )
        points.append(
            {
                "date": day,
                "portfolio_return": None,
                "benchmark_return": benchmark_return,
                "holding_return": holding_return,
            }
        )

    return {
        "instrument_id": instrument_id,
        "window": window,
        "metric": "absolute",
        "benchmark": benchmark,
        "as_of": as_of,
        "start": start,
        "available": True,
        "incomplete": incomplete,
        "points": points,
    }
