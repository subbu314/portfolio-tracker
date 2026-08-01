from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.orm import Session

from portfolio_tracker.db.models import (
    BenchmarkPrice,
    HoldingsSnapshot,
    Instrument,
    Price,
    Transaction,
)

TradeTuple = tuple[str, str, float, float, float]


@dataclass
class PortfolioInputs:
    instruments: list[Instrument]
    snapshots: dict[int, HoldingsSnapshot]
    transactions_by_instrument: dict[int, list[Transaction]]


def _load_transactions_by_instrument(
    session: Session, as_of: str
) -> dict[int, list[Transaction]]:
    rows = (
        session.query(Transaction)
        .filter(Transaction.trade_date <= as_of)
        .order_by(Transaction.trade_date.asc())
        .all()
    )
    transactions_by_instrument: dict[int, list[Transaction]] = {}
    for transaction in rows:
        transactions_by_instrument.setdefault(
            transaction.instrument_id, []
        ).append(transaction)
    return transactions_by_instrument


def _load_snapshots(
    session: Session, as_of: str
) -> dict[int, HoldingsSnapshot]:
    rows = (
        session.query(HoldingsSnapshot)
        .filter(HoldingsSnapshot.as_of <= as_of)
        .order_by(HoldingsSnapshot.as_of.asc())
        .all()
    )
    return {snapshot.instrument_id: snapshot for snapshot in rows}


def load_portfolio_inputs(session: Session, as_of: str) -> PortfolioInputs:
    """Load instruments, snapshots, and transactions once per portfolio read."""
    return PortfolioInputs(
        instruments=session.query(Instrument).all(),
        snapshots=_load_snapshots(session, as_of),
        transactions_by_instrument=_load_transactions_by_instrument(
            session, as_of
        ),
    )


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
    transactions: list[Transaction],
    snapshot: HoldingsSnapshot | None,
) -> tuple[float, float]:
    if snapshot:
        quantity = 0.0 if abs(snapshot.quantity) < 1e-8 else snapshot.quantity
        return quantity, snapshot.avg_price
    quantity, avg = _position_from_transactions(transactions)
    if abs(quantity) < 1e-8:
        return 0.0, avg
    return quantity, avg
