import pytest
from fastapi.testclient import TestClient

from portfolio_tracker.db.engine import get_session_factory
from portfolio_tracker.db.models import HoldingsSnapshot, Instrument, Setting, Transaction
from portfolio_tracker.main import create_app
from portfolio_tracker.modules import kite_auth, reconcile


def test_transaction_implied_qty_nets_buys_and_sells():
    Session = get_session_factory()
    with Session() as session:
        instrument = Instrument(symbol="INFY", instrument_type="equity", exchange="NSE")
        session.add(instrument)
        session.flush()
        session.add_all(
            [
                Transaction(
                    instrument_id=instrument.id,
                    trade_date="2024-01-01",
                    side="buy",
                    quantity=10,
                    price=100,
                    fees=0,
                    source="csv",
                    dedupe_key="implied-buy",
                ),
                Transaction(
                    instrument_id=instrument.id,
                    trade_date="2024-01-02",
                    side="sell",
                    quantity=4,
                    price=110,
                    fees=0,
                    source="csv",
                    dedupe_key="implied-sell",
                ),
            ]
        )
        session.commit()

        assert reconcile.transaction_implied_qty(session, instrument.id) == 6


def test_reconcile_detects_holdings_quantity_mismatch():
    Session = get_session_factory()
    with Session() as session:
        instrument = Instrument(
            symbol="RELIANCE",
            instrument_type="equity",
            exchange="NSE",
        )
        session.add(instrument)
        session.flush()
        session.add(
            Transaction(
                instrument_id=instrument.id,
                trade_date="2024-01-01",
                side="buy",
                quantity=5,
                price=100,
                fees=0,
                source="csv",
                dedupe_key="reconcile-buy",
            )
        )
        session.add(
            HoldingsSnapshot(
                instrument_id=instrument.id,
                quantity=10,
                avg_price=100,
                as_of="2024-06-01",
            )
        )
        session.commit()

        diffs = reconcile.reconcile_holdings(session)

        assert diffs == [
            {
                "instrument_id": instrument.id,
                "symbol": "RELIANCE",
                "holdings_qty": 10,
                "tx_qty": 5,
                "delta": 5,
            }
        ]


def test_reconcile_omits_matching_holdings():
    Session = get_session_factory()
    with Session() as session:
        instrument = Instrument(symbol="TCS", instrument_type="equity", exchange="NSE")
        session.add(instrument)
        session.flush()
        session.add(
            Transaction(
                instrument_id=instrument.id,
                trade_date="2024-01-01",
                side="buy",
                quantity=5,
                price=100,
                fees=0,
                source="csv",
                dedupe_key="matching-buy",
            )
        )
        session.add(
            HoldingsSnapshot(
                instrument_id=instrument.id,
                quantity=5,
                avg_price=100,
                as_of="2024-06-01",
            )
        )
        session.commit()

        assert reconcile.reconcile_holdings(session) == []


def test_detect_gaps_returns_missing_calendar_date_range():
    Session = get_session_factory()
    with Session() as session:
        session.add(
            Setting(
                key=kite_auth.LAST_APPEND_KEY,
                value="2024-01-01T10:00:00+05:30",
            )
        )
        session.commit()

        gap = reconcile.detect_gaps(session, today="2024-01-10")

        assert gap is not None
        assert gap["suggested_from"] == "2024-01-02"
        assert gap["suggested_to"] == "2024-01-10"
        assert "Equity and/or Mutual Funds" in gap["message"]
        assert "no manual edits" in gap["message"]


@pytest.mark.parametrize(
    ("last_append_at", "today"),
    [
        (None, "2024-01-10"),
        ("2024-01-09T10:00:00+05:30", "2024-01-10"),
        ("2024-01-10T10:00:00+05:30", "2024-01-10"),
    ],
)
def test_detect_gaps_ignores_complete_or_untracked_ranges(last_append_at, today):
    Session = get_session_factory()
    with Session() as session:
        if last_append_at:
            kite_auth.set_setting(session, kite_auth.LAST_APPEND_KEY, last_append_at)
            session.commit()

        assert reconcile.detect_gaps(session, today=today) is None


def test_get_alerts_combines_connection_reconcile_and_gap_status():
    Session = get_session_factory()
    with Session() as session:
        kite_auth.set_setting(session, kite_auth.TOKEN_KEY, "token")
        kite_auth.set_setting(
            session,
            kite_auth.LAST_APPEND_KEY,
            "2024-01-01T10:00:00+05:30",
        )
        session.commit()

        alerts = reconcile.get_alerts(session, today="2024-01-10")

        assert alerts["token_connected"] is True
        assert alerts["credentials_configured"] is True
        assert alerts["reconcile"] == []
        assert alerts["gap"]["suggested_from"] == "2024-01-02"


def test_portfolio_alerts_endpoint_exposes_alert_payload():
    response = TestClient(create_app()).get("/portfolio/alerts")

    assert response.status_code == 200
    assert response.json() == {
        "token_connected": False,
        "credentials_configured": True,
        "reconcile": [],
        "gap": None,
    }
