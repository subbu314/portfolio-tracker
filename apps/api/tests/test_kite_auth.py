from unittest.mock import MagicMock, patch

from portfolio_tracker.db.engine import get_session_factory
from portfolio_tracker.modules import kite_auth


def test_exchange_stores_token_without_exposing_secret():
    Session = get_session_factory()
    with Session() as session:
        fake_kite = MagicMock()
        fake_kite.generate_session.return_value = {
            "access_token": "secret_access_token",
            "login_time": "2026-08-01 09:00:00",
        }
        with patch.object(kite_auth, "_build_kite", return_value=fake_kite):
            result = kite_auth.exchange_request_token(session, "req_tok")
        session.commit()
        assert result == {"connected": True}
        assert kite_auth.get_access_token(session) == "secret_access_token"
        assert kite_auth.is_token_valid(session) is True


def test_missing_credentials_login_url_raises():
    from portfolio_tracker.config import get_settings

    get_settings.cache_clear()
    import os

    os.environ["KITE_API_KEY"] = ""
    get_settings.cache_clear()
    try:
        raised = False
        try:
            kite_auth.get_login_url()
        except kite_auth.KiteConfigError:
            raised = True
        assert raised
    finally:
        os.environ["KITE_API_KEY"] = "test_key"
        get_settings.cache_clear()
