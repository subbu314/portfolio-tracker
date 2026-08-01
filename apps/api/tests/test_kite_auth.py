from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from kiteconnect.exceptions import TokenException

from portfolio_tracker.db.engine import get_session_factory
from portfolio_tracker.modules import app_settings, kite_auth


def test_app_settings_round_trip():
    Session = get_session_factory()
    with Session() as session:
        app_settings.set_setting(session, "probe_key", "probe_value")
        session.commit()
        assert app_settings.get_setting(session, "probe_key") == "probe_value"


def test_token_updated_key_preserves_existing_setting_name():
    assert app_settings.TOKEN_UPDATED_KEY == "kite_token_updated_at"


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


def test_invalidate_on_kite_auth_error_clears_token():
    Session = get_session_factory()
    with Session() as session:
        app_settings.set_setting(session, app_settings.TOKEN_KEY, "secret_access_token")
        app_settings.set_setting(
            session, app_settings.TOKEN_UPDATED_KEY, "2026-08-01T09:00:00+00:00"
        )
        session.commit()

        invalidated = kite_auth.invalidate_on_kite_error(
            session, TokenException("access token secret_access_token has expired")
        )
        session.commit()

        assert invalidated is True
        assert kite_auth.get_access_token(session) is None
        assert app_settings.get_setting(session, app_settings.TOKEN_UPDATED_KEY) is None


def test_invalidate_on_non_auth_error_preserves_token():
    Session = get_session_factory()
    with Session() as session:
        app_settings.set_setting(session, app_settings.TOKEN_KEY, "secret_access_token")
        session.commit()

        invalidated = kite_auth.invalidate_on_kite_error(session, RuntimeError("upstream timeout"))
        session.commit()

        assert invalidated is False
        assert kite_auth.get_access_token(session) == "secret_access_token"


def test_exchange_auth_failure_preserves_existing_access_token():
    Session = get_session_factory()
    with Session() as session:
        app_settings.set_setting(session, app_settings.TOKEN_KEY, "old_secret_token")
        app_settings.set_setting(
            session, app_settings.TOKEN_UPDATED_KEY, "2026-08-01T09:00:00+00:00"
        )
        session.commit()
        fake_kite = MagicMock()
        fake_kite.generate_session.side_effect = TokenException(
            "request token req_secret and old_secret_token expired"
        )

        with patch.object(kite_auth, "_build_kite", return_value=fake_kite):
            with pytest.raises(kite_auth.KiteAuthError, match="^Token exchange failed$") as error:
                kite_auth.exchange_request_token(session, "req_secret")

        assert "req_secret" not in str(error.value)
        assert "old_secret_token" not in str(error.value)
        assert kite_auth.get_access_token(session) == "old_secret_token"
        assert (
            app_settings.get_setting(session, app_settings.TOKEN_UPDATED_KEY)
            == "2026-08-01T09:00:00+00:00"
        )


def test_callback_does_not_expose_upstream_error_text():
    from portfolio_tracker.main import create_app

    raw_error = "request token req_secret rejected with access token access_secret"
    with (
        patch.object(
            kite_auth,
            "exchange_request_token",
            side_effect=kite_auth.KiteAuthError(raw_error),
        ),
        TestClient(create_app()) as client,
    ):
        response = client.post("/auth/callback", json={"request_token": "req_secret"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Token exchange failed"}
    assert raw_error not in response.text
    assert "req_secret" not in response.text
    assert "access_secret" not in response.text


def test_status_and_logout_reflect_connection_state():
    from portfolio_tracker.main import create_app

    Session = get_session_factory()
    with Session() as session:
        app_settings.set_setting(session, app_settings.TOKEN_KEY, "secret_access_token")
        session.commit()

    with TestClient(create_app()) as client:
        status_response = client.get("/auth/status")
        logout_response = client.post("/auth/logout")
        disconnected_response = client.get("/auth/status")

    assert status_response.status_code == 200
    assert status_response.json()["connected"] is True
    assert logout_response.status_code == 200
    assert logout_response.json() == {"connected": False}
    assert disconnected_response.json()["connected"] is False


def test_auth_callback_get_exchanges_request_token(monkeypatch):
    from portfolio_tracker.main import create_app
    from fastapi.testclient import TestClient

    monkeypatch.setenv("KITE_API_KEY", "test_key")
    monkeypatch.setenv("KITE_API_SECRET", "test_secret")
    from portfolio_tracker.config import get_settings
    get_settings.cache_clear()

    def fake_exchange(session, request_token: str):
        assert request_token == "req_abc"
        return {"connected": True}

    monkeypatch.setattr(
        "portfolio_tracker.modules.kite_auth.exchange_request_token",
        fake_exchange,
    )
    client = TestClient(create_app())
    response = client.get("/auth/callback", params={"request_token": "req_abc", "status": "success"})
    assert response.status_code == 200
    assert response.json() == {"connected": True}
