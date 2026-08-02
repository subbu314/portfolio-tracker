"""Pure metric functions: absolute return, CAGR, XIRR, and benchmark excess.

No I/O. All dates are ISO strings ("YYYY-MM-DD"). Day counts use actual/365
(not 365.25) so that whole-year spans annualize to exact rates.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Callable, Iterable

CashFlow = tuple[str, float]  # (YYYY-MM-DD, amount); buys negative, sells/terminal positive

WINDOW_DAYS: dict[str, int | None] = {"ITD": None, "1Y": 365, "3Y": 1095, "5Y": 1825}

DAYS_PER_YEAR = 365.0


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def window_start(as_of: str, window: str, inception_date: str) -> str | None:
    """Trailing window start, or None if inception postdates it (insufficient history)."""
    if window == "ITD":
        return inception_date
    days = WINDOW_DAYS.get(window)
    if days is None:
        raise ValueError(f"Unknown window: {window}")
    start = _parse_date(as_of) - timedelta(days=days)
    if _parse_date(inception_date) > start:
        return None
    return start.isoformat()


def absolute_return(invested_cost: float, current_value: float) -> dict:
    gain = current_value - invested_cost
    pct = (gain / invested_cost) if invested_cost > 0 else None
    return {
        "gain_inr": gain,
        "gain_pct": pct,
        "invested_cost": invested_cost,
        "current_value": current_value,
    }


def invested_cost_from_transactions(txs: Iterable[tuple[str, float, float, float]]) -> float:
    """Proportional avg-cost invested cost. txs: (side, qty, price, fees)."""
    qty = 0.0
    cost = 0.0
    for side, q, price, fees in txs:
        if side == "buy":
            cost += q * price + fees
            qty += q
        elif side == "sell":
            if qty <= 0:
                continue
            avg = cost / qty
            sell_qty = min(q, qty)
            cost -= avg * sell_qty
            qty -= sell_qty
    return max(cost, 0.0)


def cagr(start_value: float, end_value: float, start_date: str, end_date: str) -> float | None:
    if start_value <= 0:
        return None
    days = (_parse_date(end_date) - _parse_date(start_date)).days
    if days < 365:
        return None
    years = days / DAYS_PER_YEAR
    return (end_value / start_value) ** (1 / years) - 1


def _xnpv(rate: float, amounts: list[float], day_offsets: list[float]) -> float:
    return sum(a / (1.0 + rate) ** (d / DAYS_PER_YEAR) for a, d in zip(amounts, day_offsets))


def xirr(cashflows: list[CashFlow]) -> float | None:
    """Internal rate of return for irregularly-dated cashflows (actual/365).

    numpy_financial has no xirr (only evenly-spaced irr), so this is a bisection
    solver on the XNPV function: sum(cf_i / (1+r)^(days_i/365)) == 0.
    """
    try:
        if len(cashflows) < 2:
            return None
        amounts = [c[1] for c in cashflows]
        if all(a <= 0 for a in amounts) or all(a >= 0 for a in amounts):
            return None
        dates = [_parse_date(c[0]) for c in cashflows]
        t0 = min(dates)
        day_offsets = [(d - t0).days for d in dates]
        if max(day_offsets) == 0:
            return None

        low, high = -0.999999, 10.0
        f_low = _xnpv(low, amounts, day_offsets)
        f_high = _xnpv(high, amounts, day_offsets)
        expansions = 0
        while f_low * f_high > 0 and high < 1e6 and expansions < 60:
            high *= 2
            f_high = _xnpv(high, amounts, day_offsets)
            expansions += 1
        if f_low * f_high > 0:
            return None

        mid = 0.0
        for _ in range(200):
            mid = (low + high) / 2
            f_mid = _xnpv(mid, amounts, day_offsets)
            if abs(f_mid) < 1e-9 or (high - low) < 1e-12:
                break
            if f_low * f_mid < 0:
                high = mid
            else:
                low = mid
                f_low = f_mid
        return mid
    except (ZeroDivisionError, OverflowError, ValueError):
        return None


def benchmark_return(start_price: float, end_price: float) -> float | None:
    if start_price <= 0:
        return None
    return (end_price / start_price) - 1


def point_to_point_return(start_value: float, end_value: float) -> float | None:
    if start_value <= 0:
        return None
    return (end_value / start_value) - 1


def excess_pp(portfolio_return: float, benchmark_return: float) -> float:
    """(portfolio - benchmark) * 100, in percentage points.

    Callers must pass unit-matched returns per the locked excess rules:
    absolute vs point-to-point bench %, CAGR vs bench CAGR, XIRR vs
    benchmark_xirr_from_trades — never XIRR vs a raw point-to-point bench return.
    """
    return (portfolio_return - benchmark_return) * 100.0


def build_xirr_cashflows(
    trades: list[tuple[str, str, float, float, float]],
    terminal_value: float,
    as_of: str,
) -> list[CashFlow]:
    """trades: (trade_date, side, qty, price, fees). Appends terminal MV at as_of."""
    flows: list[CashFlow] = []
    for trade_date, side, qty, price, fees in trades:
        notional = qty * price
        if side == "buy":
            flows.append((trade_date, -(notional + fees)))
        else:
            flows.append((trade_date, notional - fees))
    flows.append((as_of, terminal_value))
    flows.sort(key=lambda x: x[0])
    return flows


def build_rolling_xirr_cashflows(
    *,
    opening_mv: float,
    window_start: str,
    trades_in_window: list[tuple[str, str, float, float, float]],
    terminal_mv: float,
    as_of: str,
) -> list[CashFlow]:
    """Opening MV as synthetic buy at window_start + in-window trades + terminal MV at as_of."""
    flows: list[CashFlow] = []
    if opening_mv > 0:
        flows.append((window_start, -opening_mv))
    for trade_date, side, qty, price, fees in trades_in_window:
        notional = qty * price
        if side == "buy":
            flows.append((trade_date, -(notional + fees)))
        else:
            flows.append((trade_date, notional - fees))
    flows.append((as_of, terminal_mv))
    flows.sort(key=lambda x: x[0])
    return flows


def index_units_terminal_mv(
    trades: list[tuple[str, str, float, float, float]],
    index_price_on: Callable[[str], float | None],
    as_of: str,
    *,
    opening_mv: float = 0.0,
    window_start: str | None = None,
) -> float | None:
    """Same ₹ notionals as trades, invested into an index; returns terminal MV of index units."""
    units = 0.0
    if opening_mv > 0:
        if not window_start:
            return None
        px0 = index_price_on(window_start)
        if px0 is None or px0 <= 0:
            return None
        units += opening_mv / px0
    for trade_date, side, qty, price, fees in trades:
        px = index_price_on(trade_date)
        if px is None or px <= 0:
            return None
        notional = qty * price
        if side == "buy":
            units += (notional + fees) / px
        else:
            units -= max(notional - fees, 0.0) / px
    end = index_price_on(as_of)
    if end is None or end <= 0:
        return None
    return max(units, 0.0) * end


def benchmark_xirr_from_trades(
    trades: list[tuple[str, str, float, float, float]],
    index_price_on: Callable[[str], float | None],
    as_of: str,
    *,
    opening_mv: float = 0.0,
    window_start: str | None = None,
) -> float | None:
    """XIRR of the same ₹ cashflows/dates invested into the mapped index (unit-correct peer for port XIRR)."""
    terminal = index_units_terminal_mv(
        trades,
        index_price_on,
        as_of,
        opening_mv=opening_mv,
        window_start=window_start,
    )
    if terminal is None:
        return None
    if opening_mv > 0 and window_start:
        flows = build_rolling_xirr_cashflows(
            opening_mv=opening_mv,
            window_start=window_start,
            trades_in_window=trades,
            terminal_mv=terminal,
            as_of=as_of,
        )
    else:
        flows = build_xirr_cashflows(trades, terminal, as_of)
    return xirr(flows)


def rolling_absolute(
    *,
    opening_mv: float,
    terminal_mv: float,
    trades_in_window: list[tuple[str, float, float, float]] | None = None,
) -> dict:
    """Point-to-point opening_mv → terminal_mv when a position existed at window start.

    Falls back to invested_cost from in-window txs only (buys/sells in window,
    excluding opening position) vs terminal_mv when there was no opening position.
    trades_in_window (fallback path): (side, qty, price, fees).
    """
    if opening_mv > 0:
        pct = point_to_point_return(opening_mv, terminal_mv)
        return {
            "gain_inr": terminal_mv - opening_mv,
            "gain_pct": pct,
            "invested_cost": opening_mv,
            "current_value": terminal_mv,
        }
    cost = invested_cost_from_transactions(trades_in_window or [])
    return absolute_return(invested_cost=cost, current_value=terminal_mv)


def rolling_cagr(
    *,
    opening_mv: float,
    terminal_mv: float,
    window_start: str,
    as_of: str,
) -> float | None:
    if opening_mv <= 0:
        return None
    return cagr(opening_mv, terminal_mv, window_start, as_of)


def window_metric_bundle(
    *,
    absolute: dict | None,
    xirr_value: float | None,
    cagr_value: float | None,
    bench_return: float | None,
    bench_cagr: float | None,
    bench_xirr: float | None,
) -> dict:
    """Assemble the {absolute, xirr, cagr, benchmark_return, *_excess_pp} bundle for a window.

    Locked excess units: absolute vs point-to-point bench %, CAGR vs bench CAGR,
    XIRR vs benchmark_xirr_from_trades (never XIRR vs raw point-to-point bench).
    """
    abs_pct = absolute["gain_pct"] if absolute else None

    absolute_excess_pp = (
        excess_pp(abs_pct, bench_return) if abs_pct is not None and bench_return is not None else None
    )
    cagr_excess_pp = (
        excess_pp(cagr_value, bench_cagr) if cagr_value is not None and bench_cagr is not None else None
    )
    xirr_excess_pp = (
        excess_pp(xirr_value, bench_xirr) if xirr_value is not None and bench_xirr is not None else None
    )

    return {
        "absolute": absolute,
        "xirr": xirr_value,
        "cagr": cagr_value,
        "benchmark_return": bench_return,
        "absolute_excess_pp": absolute_excess_pp,
        "cagr_excess_pp": cagr_excess_pp,
        "xirr_excess_pp": xirr_excess_pp,
    }
