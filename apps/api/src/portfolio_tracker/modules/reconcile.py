from datetime import date, timedelta

from sqlalchemy.orm import Session

from portfolio_tracker.db.models import HoldingsSnapshot, Instrument, Transaction
from portfolio_tracker.modules import kite_auth


def transaction_implied_qty(session: Session, instrument_id: int) -> float:
    transactions = session.query(Transaction).filter(
        Transaction.instrument_id == instrument_id
    )
    return sum(
        transaction.quantity if transaction.side == "buy" else -transaction.quantity
        for transaction in transactions
    )


def reconcile_holdings(session: Session) -> list[dict]:
    diffs = []
    for snapshot in session.query(HoldingsSnapshot):
        transaction_qty = transaction_implied_qty(session, snapshot.instrument_id)
        delta = snapshot.quantity - transaction_qty
        if abs(delta) <= 1e-6:
            continue
        instrument = session.get(Instrument, snapshot.instrument_id)
        diffs.append(
            {
                "instrument_id": snapshot.instrument_id,
                "symbol": instrument.symbol if instrument else str(snapshot.instrument_id),
                "holdings_qty": snapshot.quantity,
                "tx_qty": transaction_qty,
                "delta": delta,
            }
        )
    return diffs


def detect_gaps(session: Session, today: str) -> dict | None:
    last_append_at = kite_auth.get_setting(session, kite_auth.LAST_APPEND_KEY)
    if not last_append_at:
        return None
    last_append_date = date.fromisoformat(last_append_at[:10])
    today_date = date.fromisoformat(today)
    if today_date - last_append_date <= timedelta(days=1):
        return None
    suggested_from = (last_append_date + timedelta(days=1)).isoformat()
    return {
        "suggested_from": suggested_from,
        "suggested_to": today,
        "message": (
            f"Possible missing trades from {suggested_from} to {today}. "
            "Export Console Tradebook for Equity and/or Mutual Funds for this range, "
            "then import the CSV or use Sync now; transactions allow no manual edits."
        ),
    }


def get_alerts(session: Session, today: str) -> dict:
    auth_status = kite_auth.get_auth_status(session)
    return {
        "token_connected": auth_status["connected"],
        "credentials_configured": auth_status["credentials_configured"],
        "reconcile": reconcile_holdings(session),
        "gap": detect_gaps(session, today),
    }
