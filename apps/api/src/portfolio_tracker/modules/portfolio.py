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
    row = (
        session.query(BenchmarkPrice)
        .filter(BenchmarkPrice.index_symbol == index_name, date_filter)
        .order_by(order)
        .first()
    )
    return row.close if row else None


def _instrument_price_symbol(instrument: Instrument) -> str:
    if instrument.instrument_type == "mf":
        return instrument.isin or instrument.symbol
    return instrument.yahoo_symbol or f"{instrument.symbol}.NS"


def _benchmark_price_fn(
    session: Session,
    index_name: str,
) -> Callable[[str], float | None]:
    def price_on(day: str) -> float | None:
        price = _benchmark_price(session, index_name, day)
        if price is not None:
            return price
        return _benchmark_price(session, index_name, day, on_or_after=True)

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
        session, benchmark_name, first_date, on_or_after=True
    )
    benchmark_end = _benchmark_price(session, benchmark_name, as_of)
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
        _benchmark_price_fn(session, benchmark_name),
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
        holdings.append(
            {
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
                "windows": {"ITD": bundle},
                "_benchmark_cagr": benchmark_cagr,
            }
        )
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
        _benchmark_price_fn(session, benchmark_map.benchmark_index),
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
        "windows": {"ITD": bundle},
    }
