from __future__ import annotations

from sqlalchemy.orm import Session

from portfolio_tracker.db.models import Instrument, Transaction
from portfolio_tracker.modules import benchmarks, metrics
from portfolio_tracker.modules.portfolio.data import (
    PortfolioInputs,
    _benchmark_price,
    _benchmark_price_fn,
    _instrument_price_symbol,
    _latest_price,
    _position,
    _trade_tuples,
    load_portfolio_inputs,
)
from portfolio_tracker.modules.portfolio.types import (
    HoldingComputed,
    HoldingPublic,
)
from portfolio_tracker.modules.portfolio.windows import (
    _build_instrument_windows,
    _build_portfolio_windows,
)


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


def _get_holdings_computed(
    session: Session,
    as_of: str,
    *,
    inputs: PortfolioInputs | None = None,
) -> list[HoldingComputed]:
    inputs = inputs or load_portfolio_inputs(session, as_of)
    holdings: list[HoldingComputed] = []
    for instrument in inputs.instruments:
        transactions = inputs.transactions_by_instrument.get(instrument.id, [])
        quantity, average_price = _position(
            transactions,
            inputs.snapshots.get(instrument.id),
        )
        if quantity <= 0 and not transactions:
            continue
        ltp = _latest_price(session, _instrument_price_symbol(instrument), as_of)
        value = ltp * quantity if ltp is not None else None
        bundle, benchmark_name, benchmark_cagr = _instrument_metrics(
            session, instrument, transactions, value, as_of
        )
        absolute = bundle["absolute"]
        public_without_windows = {
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
        }
        first_date = transactions[0].trade_date if transactions else as_of
        windows = _build_instrument_windows(
            session,
            instrument,
            transactions,
            first_date,
            as_of,
            public_without_windows,
        )
        public: HoldingPublic = {
            **public_without_windows,
            "windows": windows,
        }
        holdings.append(
            {
                "public": public,
                "benchmark_cagr": benchmark_cagr,
            }
        )
    return holdings


def get_holdings(
    session: Session,
    as_of: str,
    *,
    inputs: PortfolioInputs | None = None,
) -> list[HoldingPublic]:
    return [
        computed["public"]
        for computed in _get_holdings_computed(
            session,
            as_of,
            inputs=inputs,
        )
    ]


def _append_weighted_benchmarks(
    computed: HoldingComputed,
    total_value: float,
    weighted_returns: list[tuple[float, float]],
    weighted_cagrs: list[tuple[float, float]],
) -> None:
    holding = computed["public"]
    value = holding["value"]
    if value is None or total_value <= 0:
        return
    weight = value / total_value
    if holding["benchmark_return"] is not None:
        weighted_returns.append((weight, holding["benchmark_return"]))
    if computed["benchmark_cagr"] is not None:
        weighted_cagrs.append((weight, computed["benchmark_cagr"]))


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
    holdings: list[HoldingComputed],
    transactions_by_instrument: dict[int, list[Transaction]],
    total_value: float,
    as_of: str,
) -> tuple[float | None, float | None, float | None]:
    weighted_returns: list[tuple[float, float]] = []
    weighted_cagrs: list[tuple[float, float]] = []
    benchmark_terminal = 0.0
    terminal_is_complete = True
    for computed in holdings:
        holding = computed["public"]
        _append_weighted_benchmarks(
            computed,
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


def _get_overview_from_computed(
    session: Session,
    as_of: str,
    computed_holdings: list[HoldingComputed],
    inputs: PortfolioInputs,
) -> dict:
    holdings = [computed["public"] for computed in computed_holdings]
    total_value = sum(holding["value"] or 0.0 for holding in holdings)
    transactions_by_instrument = inputs.transactions_by_instrument
    all_transactions = sorted(
        (
            transaction
            for transactions in transactions_by_instrument.values()
            for transaction in transactions
        ),
        key=lambda transaction: transaction.trade_date,
    )
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
            computed_holdings,
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
    windows, window_skipped = _build_portfolio_windows(
        session,
        all_transactions=all_transactions,
        first_date=first_date,
        as_of=as_of,
        total_value=total_value,
        itd_bundle=bundle,
        holdings=holdings,
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
        "incomplete": any(holding["incomplete"] for holding in holdings)
        or window_skipped,
        "windows": windows,
    }


def get_overview(
    session: Session,
    as_of: str,
    *,
    inputs: PortfolioInputs | None = None,
) -> dict:
    inputs = inputs or load_portfolio_inputs(session, as_of)
    holdings = _get_holdings_computed(
        session,
        as_of,
        inputs=inputs,
    )
    return _get_overview_from_computed(
        session,
        as_of,
        holdings,
        inputs,
    )


def get_performance(session: Session, as_of: str) -> dict:
    inputs = load_portfolio_inputs(session, as_of)
    computed_holdings = _get_holdings_computed(
        session,
        as_of,
        inputs=inputs,
    )
    holdings = [computed["public"] for computed in computed_holdings]
    overview = _get_overview_from_computed(
        session,
        as_of,
        computed_holdings,
        inputs,
    )
    contributors = sorted(
        [
            {
                "symbol": holding["symbol"],
                "absolute_excess_pp": holding["absolute_excess_pp"],
                "xirr_excess_pp": holding["xirr_excess_pp"],
                "cagr_excess_pp": holding["cagr_excess_pp"],
                "value": holding["value"],
                "weight": (
                    holding["value"] / overview["total_value"]
                    if holding["value"] and overview["total_value"]
                    else 0.0
                ),
                "windows": holding["windows"],
            }
            for holding in holdings
            if holding["absolute_excess_pp"] is not None
            or holding["xirr_excess_pp"] is not None
        ],
        key=lambda row: (
            row["absolute_excess_pp"] is not None,
            row["absolute_excess_pp"] or 0.0,
        ),
        reverse=True,
    )
    return {
        **overview,
        "contributors": contributors,
        "holdings": holdings,
        "windows_available": [
            window
            for window, value in overview["windows"].items()
            if value is not None
        ],
        "default_window": "ITD",
    }
