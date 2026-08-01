from __future__ import annotations

from datetime import datetime
from typing import TypedDict
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from portfolio_tracker.db.models import HoldingsSnapshot, Instrument, Transaction
from portfolio_tracker.modules import kite_auth
from portfolio_tracker.modules.csv_import import get_or_create_instrument

IST = ZoneInfo("Asia/Kolkata")


class SyncResult(TypedDict):
    holdings_count: int
    trades_appended: int
    last_sync_at: str


def _today_ist() -> str:
    return datetime.now(IST).date().isoformat()


def _upsert_holding(
    session: Session, instrument: Instrument, quantity: float, average_price: float, as_of: str
) -> None:
    snapshot = (
        session.query(HoldingsSnapshot)
        .filter(HoldingsSnapshot.instrument_id == instrument.id)
        .first()
    )
    if snapshot is None:
        session.add(
            HoldingsSnapshot(
                instrument_id=instrument.id,
                quantity=quantity,
                avg_price=average_price,
                as_of=as_of,
            )
        )
        return
    snapshot.quantity = quantity
    snapshot.avg_price = average_price
    snapshot.as_of = as_of


def _sync_holding(session: Session, holding: dict, as_of: str, instrument_type: str) -> None:
    symbol = holding.get("tradingsymbol") or holding.get("isin")
    instrument = get_or_create_instrument(
        session,
        symbol=symbol,
        isin=holding.get("isin"),
        instrument_type=instrument_type,
        exchange=holding.get("exchange"),
    )
    quantity = float(holding.get("quantity") or 0)
    average_price = float(
        holding.get("average_price") or holding.get("last_price") or 0
    )
    _upsert_holding(session, instrument, quantity, average_price, as_of)


def _append_trade(session: Session, trade: dict, as_of: str) -> bool:
    fill_date = str(trade.get("fill_timestamp") or "")[:10]
    if fill_date != as_of:
        return False
    symbol = trade["tradingsymbol"]
    side = "buy" if str(trade.get("transaction_type", "")).upper() == "BUY" else "sell"
    quantity = float(trade["quantity"])
    price = float(trade.get("average_price") or trade.get("price") or 0)
    order_id = str(trade.get("trade_id") or trade.get("order_id"))
    dedupe_key = f"api:{symbol}:{fill_date}:{side}:{quantity}:{price}:{order_id}"
    if session.query(Transaction).filter(Transaction.dedupe_key == dedupe_key).first():
        return False
    instrument = get_or_create_instrument(
        session,
        symbol=symbol,
        isin=trade.get("isin"),
        instrument_type="equity",
        exchange=trade.get("exchange"),
    )
    session.add(
        Transaction(
            instrument_id=instrument.id,
            trade_date=fill_date,
            side=side,
            quantity=quantity,
            price=price,
            fees=0.0,
            source="api",
            dedupe_key=dedupe_key,
            raw_order_id=order_id,
        )
    )
    return True


def _fetch_kite_data(session: Session, kite) -> tuple[list[dict], list[dict], list[dict]]:
    try:
        return (
            kite.holdings() or [],
            kite.mf_holdings() or [],
            kite.trades() or [],
        )
    except Exception as exc:
        if kite_auth.invalidate_on_kite_error(session, exc):
            session.commit()
            raise kite_auth.KiteAuthError(
                "Kite session expired; reconnect Zerodha"
            ) from exc
        raise


def sync_all(session: Session) -> SyncResult:
    kite = kite_auth.authenticated_kite(session)
    as_of = _today_ist()
    equity_holdings, mutual_fund_holdings, trades = _fetch_kite_data(session, kite)

    for holding in equity_holdings:
        symbol = str(holding["tradingsymbol"])
        instrument_type = "etf" if "ETF" in symbol.upper() else "equity"
        _sync_holding(session, holding, as_of, instrument_type)
    for holding in mutual_fund_holdings:
        _sync_holding(session, holding, as_of, "mf")
    appended = sum(_append_trade(session, trade, as_of) for trade in trades)

    now = datetime.now(IST).isoformat()
    kite_auth.set_setting(session, kite_auth.LAST_SYNC_KEY, now)
    kite_auth.set_setting(session, kite_auth.LAST_APPEND_KEY, now)
    return {
        "holdings_count": len(equity_holdings) + len(mutual_fund_holdings),
        "trades_appended": appended,
        "last_sync_at": now,
    }
