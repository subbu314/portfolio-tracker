from __future__ import annotations

from sqlalchemy.orm import Session

from portfolio_tracker.db.models import Instrument, Transaction
from portfolio_tracker.modules import benchmarks, metrics
from portfolio_tracker.modules.portfolio.data import (
    _benchmark_price,
    _benchmark_price_fn,
    _instrument_price_symbol,
    _latest_price,
    _trade_tuples,
)


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
) -> tuple[float | None, float | None, float | None, float | None, set[int]]:
    opening_mv = 0.0
    weighted_returns: list[tuple[float, float]] = []
    weighted_cagrs: list[tuple[float, float]] = []
    benchmark_terminal = 0.0
    terminal_is_complete = True
    skipped: set[int] = set()
    included = 0

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
            # Missing opening price — skip this name; do not null the whole window.
            skipped.add(instrument_id)
            continue
        included += 1
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

    if included == 0 and skipped:
        return None, None, None, None, skipped
    return (
        opening_mv,
        _blended_benchmark(weighted_returns),
        _blended_benchmark(weighted_cagrs),
        benchmark_terminal if terminal_is_complete else None,
        skipped,
    )


def _build_portfolio_window(
    session: Session,
    all_transactions: list[Transaction],
    transactions_by_instrument: dict[int, list[Transaction]],
    holding_values: dict[int, float],
    start: str,
    as_of: str,
    total_value: float,
) -> tuple[dict | None, bool]:
    opening_mv, benchmark_return, benchmark_cagr, benchmark_terminal, skipped = (
        _portfolio_window_benchmark_inputs(
            session,
            transactions_by_instrument,
            holding_values,
            start,
            as_of,
        )
    )
    if opening_mv is None:
        return None, bool(skipped)
    effective_total = sum(
        value
        for instrument_id, value in holding_values.items()
        if instrument_id not in skipped
    )
    in_window = [
        transaction
        for transaction in all_transactions
        if start < transaction.trade_date <= as_of
        and transaction.instrument_id not in skipped
    ]
    trades = _trade_tuples(in_window)
    in_window_sides = [
        (tx.side, tx.quantity, tx.price, tx.fees) for tx in in_window
    ]
    # Portfolio terminal MV includes capital added after window start. Naive
    # opening_mv→total_value point-to-point inflates absolute/CAGR; use invested
    # capital (opening MV + in-window net cost) vs terminal instead.
    if opening_mv > 0:
        invested = opening_mv + metrics.invested_cost_from_transactions(
            in_window_sides
        )
        absolute = metrics.absolute_return(
            invested_cost=invested,
            current_value=effective_total,
        )
        cagr_value = (
            metrics.rolling_cagr(
                opening_mv=opening_mv,
                terminal_mv=effective_total,
                window_start=start,
                as_of=as_of,
            )
            if not in_window_sides
            else None
        )
    else:
        absolute = metrics.rolling_absolute(
            opening_mv=0.0,
            terminal_mv=effective_total,
            trades_in_window=in_window_sides,
        )
        cagr_value = None
    xirr_value = metrics.xirr(
        metrics.build_rolling_xirr_cashflows(
            opening_mv=opening_mv,
            window_start=start,
            trades_in_window=trades,
            terminal_mv=effective_total,
            as_of=as_of,
        )
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
    return (
        _flatten_window_bundle(
            metrics.window_metric_bundle(
                absolute=absolute,
                xirr_value=xirr_value,
                cagr_value=cagr_value,
                bench_return=benchmark_return,
                bench_cagr=benchmark_cagr,
                bench_xirr=benchmark_xirr,
            )
        ),
        bool(skipped),
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
) -> tuple[dict, bool]:
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
    any_skipped = False
    for window in ("1Y", "3Y", "5Y"):
        start = metrics.window_start(as_of, window, first_date)
        if start is None:
            windows[window] = None
            continue
        body, skipped = _build_portfolio_window(
            session,
            all_transactions,
            transactions_by_instrument,
            holding_values,
            start,
            as_of,
            total_value,
        )
        windows[window] = body
        any_skipped = any_skipped or skipped
    return windows, any_skipped
