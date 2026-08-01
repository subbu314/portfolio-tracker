from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from kiteconnect.exceptions import TokenException

from portfolio_tracker.db.engine import get_session_factory
from portfolio_tracker.db.models import HoldingsSnapshot, Instrument, Setting, Transaction
from portfolio_tracker.modules import kite_auth, kite_sync


def test_sync_upserts_holdings_and_appends_todays_trades():
    Session = get_session_factory()
    with Session() as session:
        session.add(Setting(key=kite_auth.TOKEN_KEY, value="token"))
        session.commit()
        kite = MagicMock()
        kite.holdings.return_value = [
            {
                "tradingsymbol": "RELIANCE",
                "isin": "INE002A01018",
                "exchange": "NSE",
                "quantity": 10,
                "average_price": 2000.0,
                "instrument_type": "EQ",
            }
        ]
        kite.mf_holdings.return_value = [
            {
                "tradingsymbol": "INF090I01239",
                "isin": "INF090I01239",
                "quantity": 5,
                "average_price": 100.0,
            }
        ]
        kite.trades.return_value = [
            {
                "trade_id": "99",
                "order_id": "55",
                "tradingsymbol": "RELIANCE",
                "exchange": "NSE",
                "transaction_type": "BUY",
                "quantity": 1,
                "average_price": 2100.0,
                "fill_timestamp": "2026-08-01 10:00:00",
            }
        ]

        with (
            patch.object(kite_auth, "authenticated_kite", return_value=kite),
            patch.object(kite_sync, "_today_ist", return_value="2026-08-01"),
        ):
            result = kite_sync.sync_all(session)
        session.commit()

        assert result["holdings_count"] == 2
        assert result["trades_appended"] == 1
        assert session.query(HoldingsSnapshot).count() == 2
        assert {row.instrument_type for row in session.query(Instrument).all()} == {
            "equity",
            "mf",
        }
        assert (
            session.query(Transaction).filter(Transaction.source == "api").count() == 1
        )
        assert kite_auth.get_setting(session, kite_auth.LAST_SYNC_KEY) == result["last_sync_at"]
        assert kite_auth.get_setting(session, kite_auth.LAST_APPEND_KEY) == result["last_sync_at"]


def test_sync_is_idempotent_and_updates_existing_holdings_snapshot():
    Session = get_session_factory()
    with Session() as session:
        session.add(Setting(key=kite_auth.TOKEN_KEY, value="token"))
        session.commit()
        kite = MagicMock()
        holding = {
            "tradingsymbol": "RELIANCE",
            "isin": "INE002A01018",
            "exchange": "NSE",
            "quantity": 10,
            "average_price": 2000.0,
        }
        kite.holdings.side_effect = [[holding], [{**holding, "quantity": 11}]]
        kite.mf_holdings.return_value = []
        kite.trades.return_value = [
            {
                "trade_id": "99",
                "tradingsymbol": "RELIANCE",
                "exchange": "NSE",
                "transaction_type": "BUY",
                "quantity": 1,
                "average_price": 2100.0,
                "fill_timestamp": "2026-08-01 10:00:00",
            }
        ]

        with (
            patch.object(kite_auth, "authenticated_kite", return_value=kite),
            patch.object(kite_sync, "_today_ist", return_value="2026-08-01"),
        ):
            first = kite_sync.sync_all(session)
            session.commit()
            second = kite_sync.sync_all(session)
            session.commit()

        assert first["trades_appended"] == 1
        assert second["trades_appended"] == 0
        assert session.query(Transaction).count() == 1
        assert session.query(HoldingsSnapshot).one().quantity == 11


def test_sync_invalidates_expired_kite_token_without_exposing_upstream_error():
    Session = get_session_factory()
    with Session() as session:
        session.add(Setting(key=kite_auth.TOKEN_KEY, value="secret_access_token"))
        session.commit()
        kite = MagicMock()
        kite.holdings.side_effect = TokenException(
            "access token secret_access_token has expired"
        )

        with patch.object(kite_auth, "authenticated_kite", return_value=kite):
            with pytest.raises(
                kite_auth.KiteAuthError, match="^Kite session expired; reconnect Zerodha$"
            ) as error:
                kite_sync.sync_all(session)

        assert "secret_access_token" not in str(error.value)

    with Session() as session:
        assert kite_auth.get_access_token(session) is None


def test_sync_endpoint_requires_kite_reconnection():
    from portfolio_tracker.main import create_app

    with TestClient(create_app()) as client:
        response = client.post("/sync")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Reconnect Zerodha — access token missing or expired"
    }


def test_sync_endpoint_refreshes_non_kite_prices():
    from portfolio_tracker.main import create_app
    from portfolio_tracker.routers import sync as sync_router

    Session = get_session_factory()
    with Session() as session:
        kite_auth.set_setting(session, kite_auth.TOKEN_KEY, "token")
        session.commit()
    sync_result = {
        "holdings_count": 2,
        "trades_appended": 1,
        "last_sync_at": "2026-08-01T12:00:00+05:30",
    }
    price_result = {"updated": 3, "failed": [], "incomplete": False}

    with (
        patch.object(sync_router.kite_sync, "sync_all", return_value=sync_result),
        patch.object(sync_router, "refresh_prices", return_value=price_result),
        TestClient(create_app()) as client,
    ):
        response = client.post("/sync")

    assert response.status_code == 200
    assert response.json() == {**sync_result, "prices": price_result}
