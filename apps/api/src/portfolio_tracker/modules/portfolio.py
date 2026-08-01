from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from portfolio_tracker.db.models import (
    BenchmarkPrice,
    HoldingsSnapshot,
    Instrument,
    Price,
    Transaction,
)
from portfolio_tracker.modules import benchmarks, metrics

TradeTuple = tuple[str, str, float, float, float]


def _latest_price(session: Session, symbol: str, as_of: str) -> float | None:
    row = (
        session.query(Price)
        .filter(Price.symbol == symbol, Price.price_date <= as_of)
        .order_by(Price.price_date.desc())
        .first()
    )
    return row.close if row else None


def _benchmark_price(
    session: Session,
    index_name: str,
    day: str,
    *,
    on_or_after: bool = False,
    as_of: str | None = None,
) -> float | None:
    date_filter = (
        BenchmarkPrice.price_date >= day
        if on_or_after
        else BenchmarkPrice.price_date <= day
    )
    order = (
        BenchmarkPrice.price_date.asc()
        if on_or_after
        else BenchmarkPrice.price_date.desc()
    )
    query = session.query(BenchmarkPrice).filter(
        BenchmarkPrice.index_symbol == index_name,
        date_filter,
    )
    if as_of is not None:
        query = query.filter(BenchmarkPrice.price_date <= as_of)
    row = query.order_by(order).first()
    return row.close if row else None


def _instrument_price_symbol(instrument: Instrument) -> str:
    if instrument.instrument_type == "mf":
        return instrument.isin or instrument.symbol
    return instrument.yahoo_symbol or f"{instrument.symbol}.NS"


def _benchmark_price_fn(
    session: Session,
    index_name: str,
    as_of: str,
) -> Callable[[str], float | None]:
    def price_on(day: str) -> float | None:
        price = _benchmark_price(session, index_name, day, as_of=as_of)
        if price is not None:
            return price
        return _benchmark_price(
            session, index_name, day, on_or_after=True, as_of=as_of
        )

    return price_on


def _transactions(
    session: Session,
    instrument_id: int,
    as_of: str,
) -> list[Transaction]:
    return (
        session.query(Transaction)
        .filter(
            Transaction.instrument_id == instrument_id,
            Transaction.trade_date <= as_of,
        )
        .order_by(Transaction.trade_date.asc())
        .all()
    )


def _trade_tuples(transactions: list[Transaction]) -> list[TradeTuple]:
    return [
        (tx.trade_date, tx.side, tx.quantity, tx.price, tx.fees)
        for tx in transactions
    ]


def _position_from_transactions(
    transactions: list[Transaction],
) -> tuple[float, float]:
    quantity = 0.0
    cost = 0.0
    for tx in transactions:
        if tx.side == "buy":
            cost += tx.quantity * tx.price + tx.fees
            quantity += tx.quantity
        elif quantity > 0:
            sold_quantity = min(tx.quantity, quantity)
            cost -= (cost / quantity) * sold_quantity
            quantity -= sold_quantity
    return quantity, (cost / quantity if quantity else 0.0)


def _position(
    session: Session,
    instrument_id: int,
    as_of: str,
    transactions: list[Transaction],
) -> tuple[float, float]:
    snapshot = (
        session.query(HoldingsSnapshot)
        .filter(
            HoldingsSnapshot.instrument_id == instrument_id,
            HoldingsSnapshot.as_of <= as_of,
        )
        .first()
    )
    if snapshot:
        return snapshot.quantity, snapshot.avg_price
    return _position_from_transactions(transactions)


def _instrument_metrics(
    session: Session,
    instrument: Instrument,
    transactions: list[Transaction],
    value: float | None,
    as_of: str,
) -> tuple[dict, str, float | None]:
    trades = _trade_tuples(transactions)
    invested = metrics.invested_cost_from_transactions(
        [(tx.side, tx.quantity, tx.price, tx.fees) for tx in transactions]
    )
    absolute = metrics.absolute_return(invested, value or 0.0)
    first_date = transactions[0].trade_date if transactions else as_of
    xirr_value = metrics.xirr(
        metrics.build_xirr_cashflows(trades, value or 0.0, as_of)
    )
    cagr_value = (
        metrics.cagr(invested, value, first_date, as_of)
        if value is not None
        else None
    )
    benchmark_map = benchmarks.ensure_benchmark_map(session, instrument)
    benchmark_name = benchmark_map.benchmark_index
    benchmark_start = _benchmark_price(
        session, benchmark_name, first_date, on_or_after=True, as_of=as_of
    )
    benchmark_end = _benchmark_price(session, benchmark_name, as_of, as_of=as_of)
    benchmark_return = (
        metrics.benchmark_return(benchmark_start, benchmark_end)
        if benchmark_start is not None and benchmark_end is not None
        else None
    )
    benchmark_cagr = (
        metrics.cagr(benchmark_start, benchmark_end, first_date, as_of)
        if benchmark_start is not None and benchmark_end is not None
        else None
    )
    benchmark_xirr = metrics.benchmark_xirr_from_trades(
        trades,
        _benchmark_price_fn(session, benchmark_name, as_of),
        as_of,
    )
    bundle = metrics.window_metric_bundle(
        absolute=absolute if value is not None else None,
        xirr_value=xirr_value if value is not None else None,
        cagr_value=cagr_value,
        bench_return=benchmark_return,
        bench_cagr=benchmark_cagr,
        bench_xirr=benchmark_xirr,
    )
    return bundle, benchmark_name, benchmark_cagr


def _qty_at(transactions: list[Transaction], as_of_day: str) -> float:
    quantity = 0.0
    for transaction in transactions:
        if transaction.trade_date > as_of_day:
            break
        quantity += (
            transaction.quantity
            if transaction.side == "buy"
            else -transaction.quantity
        )
    return quantity


def _flatten_window_bundle(bundle: dict) -> dict:
    absolute = bundle.get("absolute")
    return {
        "absolute_pct": absolute.get("gain_pct") if absolute else None,
        "absolute_inr": absolute.get("gain_inr") if absolute else None,
        "xirr": bundle.get("xirr"),
        "cagr": bundle.get("cagr"),
        "benchmark_return": bundle.get("benchmark_return"),
        "absolute_excess_pp": bundle.get("absolute_excess_pp"),
        "xirr_excess_pp": bundle.get("xirr_excess_pp"),
        "cagr_excess_pp": bundle.get("cagr_excess_pp"),
    }


def _build_instrument_windows(
    session: Session,
    instrument: Instrument,
    transactions: list[Transaction],
    first_date: str,
    as_of: str,
    itd_row: dict,
) -> dict:
    windows: dict = {
        "ITD": {
            key: itd_row.get(key)
            for key in (
                "absolute_pct",
                "absolute_inr",
                "xirr",
                "cagr",
                "benchmark_return",
                "absolute_excess_pp",
                "xirr_excess_pp",
                "cagr_excess_pp",
            )
        }
    }
    price_symbol = _instrument_price_symbol(instrument)
    terminal_value = itd_row.get("value") or 0.0
    benchmark_map = benchmarks.ensure_benchmark_map(session, instrument)
    benchmark_name = benchmark_map.benchmark_index
    benchmark_price_on = _benchmark_price_fn(session, benchmark_name, as_of)

    for window in ("1Y", "3Y", "5Y"):
        start = metrics.window_start(as_of, window, first_date)
        if start is None:
            windows[window] = None
            continue

        quantity_at_start = _qty_at(transactions, start)
        opening_price = _latest_price(session, price_symbol, start)
        if quantity_at_start > 0 and opening_price is None:
            windows[window] = None
            continue
        opening_mv = (
            quantity_at_start * opening_price if quantity_at_start > 0 else 0.0
        )
        in_window = [
            transaction
            for transaction in transactions
            if start < transaction.trade_date <= as_of
        ]
        trades = _trade_tuples(in_window)
        absolute = metrics.rolling_absolute(
            opening_mv=opening_mv,
            terminal_mv=terminal_value,
            trades_in_window=[
                (tx.side, tx.quantity, tx.price, tx.fees) for tx in in_window
            ],
        )
        xirr_value = metrics.xirr(
            metrics.build_rolling_xirr_cashflows(
                opening_mv=opening_mv,
                window_start=start,
                trades_in_window=trades,
                terminal_mv=terminal_value,
                as_of=as_of,
            )
        )
        cagr_value = metrics.rolling_cagr(
            opening_mv=opening_mv,
            terminal_mv=terminal_value,
            window_start=start,
            as_of=as_of,
        )
        benchmark_start = _benchmark_price(
            session,
            benchmark_name,
            start,
            on_or_after=True,
            as_of=as_of,
        )
        benchmark_end = _benchmark_price(
            session,
            benchmark_name,
            as_of,
            as_of=as_of,
        )
        benchmark_return = (
            metrics.benchmark_return(benchmark_start, benchmark_end)
            if benchmark_start is not None and benchmark_end is not None
            else None
        )
        benchmark_cagr = (
            metrics.cagr(benchmark_start, benchmark_end, start, as_of)
            if benchmark_start is not None and benchmark_end is not None
            else None
        )
        benchmark_xirr = metrics.benchmark_xirr_from_trades(
            trades,
            benchmark_price_on,
            as_of,
            opening_mv=opening_mv,
            window_start=start,
        )
        windows[window] = _flatten_window_bundle(
            metrics.window_metric_bundle(
                absolute=absolute,
                xirr_value=xirr_value,
                cagr_value=cagr_value,
                bench_return=benchmark_return,
                bench_cagr=benchmark_cagr,
                bench_xirr=benchmark_xirr,
            )
        )
    return windows


def get_holdings(session: Session, as_of: str) -> list[dict]:
    holdings: list[dict] = []
    for instrument in session.query(Instrument).all():
        transactions = _transactions(session, instrument.id, as_of)
        quantity, average_price = _position(
            session, instrument.id, as_of, transactions
        )
        if quantity <= 0 and not transactions:
            continue
        ltp = _latest_price(session, _instrument_price_symbol(instrument), as_of)
        value = ltp * quantity if ltp is not None else None
        bundle, benchmark_name, benchmark_cagr = _instrument_metrics(
            session, instrument, transactions, value, as_of
        )
        absolute = bundle["absolute"]
        row = {
            "instrument_id": instrument.id,
            "symbol": instrument.symbol,
            "instrument_type": instrument.instrument_type,
            "qty": quantity,
            "avg_price": average_price,
            "ltp": ltp,
            "value": value,
            "absolute_pct": absolute["gain_pct"] if absolute else None,
            "absolute_inr": absolute["gain_inr"] if absolute else None,
            "xirr": bundle["xirr"],
            "cagr": bundle["cagr"],
            "benchmark": benchmark_name,
            "benchmark_return": bundle["benchmark_return"],
            "absolute_excess_pp": bundle["absolute_excess_pp"],
            "xirr_excess_pp": bundle["xirr_excess_pp"],
            "cagr_excess_pp": bundle["cagr_excess_pp"],
            "incomplete": ltp is None or bundle["benchmark_return"] is None,
            "needs_category": bool(instrument.needs_category),
            "_benchmark_cagr": benchmark_cagr,
        }
        first_date = transactions[0].trade_date if transactions else as_of
        row["windows"] = _build_instrument_windows(
            session,
            instrument,
            transactions,
            first_date,
            as_of,
            row,
        )
        holdings.append(row)
    return holdings


def _append_weighted_benchmarks(
    holding: dict,
    total_value: float,
    weighted_returns: list[tuple[float, float]],
    weighted_cagrs: list[tuple[float, float]],
) -> None:
    value = holding["value"]
    if value is None or total_value <= 0:
        return
    weight = value / total_value
    if holding["benchmark_return"] is not None:
        weighted_returns.append((weight, holding["benchmark_return"]))
    if holding["_benchmark_cagr"] is not None:
        weighted_cagrs.append((weight, holding["_benchmark_cagr"]))


def _holding_benchmark_terminal(
    session: Session,
    holding: dict,
    transactions: list[Transaction],
    as_of: str,
) -> float | None:
    instrument = session.get(Instrument, holding["instrument_id"])
    if instrument is None:
        return None
    benchmark_map = benchmarks.ensure_benchmark_map(session, instrument)
    return metrics.index_units_terminal_mv(
        _trade_tuples(transactions),
        _benchmark_price_fn(session, benchmark_map.benchmark_index, as_of),
        as_of,
    )


def _portfolio_benchmark_metrics(
    session: Session,
    holdings: list[dict],
    transactions_by_instrument: dict[int, list[Transaction]],
    total_value: float,
    as_of: str,
) -> tuple[float | None, float | None, float | None]:
    weighted_returns: list[tuple[float, float]] = []
    weighted_cagrs: list[tuple[float, float]] = []
    benchmark_terminal = 0.0
    terminal_is_complete = True
    for holding in holdings:
        _append_weighted_benchmarks(
            holding,
            total_value,
            weighted_returns,
            weighted_cagrs,
        )
        terminal = _holding_benchmark_terminal(
            session,
            holding,
            transactions_by_instrument.get(holding["instrument_id"], []),
            as_of,
        )
        if terminal is None:
            terminal_is_complete = False
        else:
            benchmark_terminal += terminal
    blended_return = (
        benchmarks.portfolio_blended_benchmark_return(weighted_returns)
        if weighted_returns
        else None
    )
    blended_cagr = (
        benchmarks.portfolio_blended_benchmark_return(weighted_cagrs)
        if weighted_cagrs
        else None
    )
    return (
        blended_return,
        blended_cagr,
        benchmark_terminal if terminal_is_complete else None,
    )


def _blended_benchmark(
    weighted_values: list[tuple[float, float]],
) -> float | None:
    total_weight = sum(weight for weight, _ in weighted_values)
    if total_weight <= 0:
        return None
    return benchmarks.portfolio_blended_benchmark_return(
        [(weight / total_weight, value) for weight, value in weighted_values]
    )


def _instrument_window_benchmark_inputs(
    session: Session,
    instrument: Instrument,
    transactions: list[Transaction],
    current_value: float,
    start: str,
    as_of: str,
) -> tuple[float | None, float | None, float | None, float | None]:
    quantity = _qty_at(transactions, start)
    price = _latest_price(
        session, _instrument_price_symbol(instrument), start
    )
    if quantity > 0 and price is None:
        return None, None, None, None
    opening_mv = quantity * price if quantity > 0 else 0.0
    benchmark_name = benchmarks.ensure_benchmark_map(
        session, instrument
    ).benchmark_index
    benchmark_start = _benchmark_price(
        session, benchmark_name, start, on_or_after=True, as_of=as_of
    )
    benchmark_end = _benchmark_price(
        session, benchmark_name, as_of, as_of=as_of
    )
    benchmark_return = (
        metrics.benchmark_return(benchmark_start, benchmark_end)
        if benchmark_start is not None and benchmark_end is not None
        and current_value > 0
        else None
    )
    benchmark_cagr = (
        metrics.cagr(benchmark_start, benchmark_end, start, as_of)
        if benchmark_start is not None and benchmark_end is not None
        and current_value > 0
        else None
    )
    in_window = [
        transaction
        for transaction in transactions
        if start < transaction.trade_date <= as_of
    ]
    benchmark_terminal = metrics.index_units_terminal_mv(
        _trade_tuples(in_window),
        _benchmark_price_fn(session, benchmark_name, as_of),
        as_of,
        opening_mv=opening_mv,
        window_start=start,
    )
    return opening_mv, benchmark_return, benchmark_cagr, benchmark_terminal


def _portfolio_window_benchmark_inputs(
    session: Session,
    transactions_by_instrument: dict[int, list[Transaction]],
    holding_values: dict[int, float],
    start: str,
    as_of: str,
) -> tuple[float | None, float | None, float | None, float | None]:
    opening_mv = 0.0
    weighted_returns: list[tuple[float, float]] = []
    weighted_cagrs: list[tuple[float, float]] = []
    benchmark_terminal = 0.0
    terminal_is_complete = True

    for instrument_id, transactions in transactions_by_instrument.items():
        instrument = session.get(Instrument, instrument_id)
        if instrument is None:
            continue
        (
            instrument_opening_mv,
            benchmark_return,
            benchmark_cagr,
            terminal,
        ) = _instrument_window_benchmark_inputs(
            session,
            instrument,
            transactions,
            holding_values.get(instrument_id, 0.0),
            start,
            as_of,
        )
        if instrument_opening_mv is None:
            return None, None, None, None
        opening_mv += instrument_opening_mv
        current_value = holding_values.get(instrument_id, 0.0)
        if benchmark_return is not None:
            weighted_returns.append((current_value, benchmark_return))
        if benchmark_cagr is not None:
            weighted_cagrs.append((current_value, benchmark_cagr))
        if terminal is None:
            terminal_is_complete = False
        else:
            benchmark_terminal += terminal

    return (
        opening_mv,
        _blended_benchmark(weighted_returns),
        _blended_benchmark(weighted_cagrs),
        benchmark_terminal if terminal_is_complete else None,
    )


def _build_portfolio_window(
    session: Session,
    all_transactions: list[Transaction],
    transactions_by_instrument: dict[int, list[Transaction]],
    holding_values: dict[int, float],
    start: str,
    as_of: str,
    total_value: float,
) -> dict | None:
    opening_mv, benchmark_return, benchmark_cagr, benchmark_terminal = (
        _portfolio_window_benchmark_inputs(
            session,
            transactions_by_instrument,
            holding_values,
            start,
            as_of,
        )
    )
    if opening_mv is None:
        return None
    in_window = [
        transaction
        for transaction in all_transactions
        if start < transaction.trade_date <= as_of
    ]
    trades = _trade_tuples(in_window)
    absolute = metrics.rolling_absolute(
        opening_mv=opening_mv,
        terminal_mv=total_value,
        trades_in_window=[
            (tx.side, tx.quantity, tx.price, tx.fees) for tx in in_window
        ],
    )
    xirr_value = metrics.xirr(
        metrics.build_rolling_xirr_cashflows(
            opening_mv=opening_mv,
            window_start=start,
            trades_in_window=trades,
            terminal_mv=total_value,
            as_of=as_of,
        )
    )
    cagr_value = metrics.rolling_cagr(
        opening_mv=opening_mv,
        terminal_mv=total_value,
        window_start=start,
        as_of=as_of,
    )
    benchmark_xirr = (
        metrics.xirr(
            metrics.build_rolling_xirr_cashflows(
                opening_mv=opening_mv,
                window_start=start,
                trades_in_window=trades,
                terminal_mv=benchmark_terminal,
                as_of=as_of,
            )
        )
        if benchmark_terminal is not None
        else None
    )
    return _flatten_window_bundle(
        metrics.window_metric_bundle(
            absolute=absolute,
            xirr_value=xirr_value,
            cagr_value=cagr_value,
            bench_return=benchmark_return,
            bench_cagr=benchmark_cagr,
            bench_xirr=benchmark_xirr,
        )
    )


def _build_portfolio_windows(
    session: Session,
    *,
    all_transactions: list[Transaction],
    first_date: str,
    as_of: str,
    total_value: float,
    itd_bundle: dict,
    holdings: list[dict],
) -> dict:
    transactions_by_instrument: dict[int, list[Transaction]] = {}
    for transaction in all_transactions:
        transactions_by_instrument.setdefault(
            transaction.instrument_id, []
        ).append(transaction)
    holding_values = {
        holding["instrument_id"]: holding["value"] or 0.0
        for holding in holdings
    }
    windows: dict = {"ITD": _flatten_window_bundle(itd_bundle)}
    for window in ("1Y", "3Y", "5Y"):
        start = metrics.window_start(as_of, window, first_date)
        windows[window] = (
            _build_portfolio_window(
                session,
                all_transactions,
                transactions_by_instrument,
                holding_values,
                start,
                as_of,
                total_value,
            )
            if start is not None
            else None
        )
    return windows


def get_overview(session: Session, as_of: str) -> dict:
    holdings = get_holdings(session, as_of)
    total_value = sum(holding["value"] or 0.0 for holding in holdings)
    all_transactions = (
        session.query(Transaction)
        .filter(Transaction.trade_date <= as_of)
        .order_by(Transaction.trade_date.asc())
        .all()
    )
    transactions_by_instrument: dict[int, list[Transaction]] = {}
    for transaction in all_transactions:
        transactions_by_instrument.setdefault(
            transaction.instrument_id, []
        ).append(transaction)
    invested = sum(
        metrics.invested_cost_from_transactions(
            [(tx.side, tx.quantity, tx.price, tx.fees) for tx in transactions]
        )
        for transactions in transactions_by_instrument.values()
    )
    absolute = metrics.absolute_return(invested, total_value)
    trades = _trade_tuples(all_transactions)
    first_date = all_transactions[0].trade_date if all_transactions else as_of
    xirr_value = metrics.xirr(
        metrics.build_xirr_cashflows(trades, total_value, as_of)
    )
    cagr_value = (
        metrics.cagr(invested, total_value, first_date, as_of)
        if invested > 0
        else None
    )
    benchmark_return, benchmark_cagr, benchmark_terminal = (
        _portfolio_benchmark_metrics(
            session,
            holdings,
            transactions_by_instrument,
            total_value,
            as_of,
        )
    )
    benchmark_xirr = (
        metrics.xirr(
            metrics.build_xirr_cashflows(
                trades,
                benchmark_terminal,
                as_of,
            )
        )
        if benchmark_terminal is not None and all_transactions
        else None
    )
    bundle = metrics.window_metric_bundle(
        absolute=absolute,
        xirr_value=xirr_value,
        cagr_value=cagr_value,
        bench_return=benchmark_return,
        bench_cagr=benchmark_cagr,
        bench_xirr=benchmark_xirr,
    )
    return {
        "as_of": as_of,
        "total_value": total_value,
        "absolute": absolute,
        "xirr": xirr_value,
        "cagr": cagr_value,
        "benchmark_return": benchmark_return,
        "absolute_excess_pp": bundle["absolute_excess_pp"],
        "xirr_excess_pp": bundle["xirr_excess_pp"],
        "cagr_excess_pp": bundle["cagr_excess_pp"],
        "allocation": [
            {
                "symbol": holding["symbol"],
                "weight": (
                    holding["value"] / total_value
                    if holding["value"] is not None and total_value
                    else 0.0
                ),
            }
            for holding in holdings
        ],
        "incomplete": any(holding["incomplete"] for holding in holdings),
        "windows": _build_portfolio_windows(
            session,
            all_transactions=all_transactions,
            first_date=first_date,
            as_of=as_of,
            total_value=total_value,
            itd_bundle=bundle,
            holdings=holdings,
        ),
    }
