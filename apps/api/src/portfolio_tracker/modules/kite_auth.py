from __future__ import annotations

from datetime import datetime, timezone

from kiteconnect import KiteConnect
from kiteconnect.exceptions import TokenException
from sqlalchemy.orm import Session

from portfolio_tracker.config import get_settings
from portfolio_tracker.db.models import Setting
from portfolio_tracker.modules import app_settings


class KiteConfigError(Exception):
    pass


class KiteAuthError(Exception):
    pass


def _build_kite(api_key: str | None = None) -> KiteConnect:
    settings = get_settings()
    key = api_key or settings.kite_api_key
    if not key:
        raise KiteConfigError("KITE_API_KEY is not configured")
    return KiteConnect(api_key=key)


def get_login_url() -> str:
    settings = get_settings()
    if not settings.kite_api_key or not settings.kite_api_secret:
        raise KiteConfigError("Kite API credentials are not configured")
    kite = _build_kite()
    return kite.login_url()


def exchange_request_token(session: Session, request_token: str) -> dict[str, bool]:
    settings = get_settings()
    if not settings.kite_api_key or not settings.kite_api_secret:
        raise KiteConfigError("Kite API credentials are not configured")
    kite = _build_kite()
    try:
        data = kite.generate_session(request_token, api_secret=settings.kite_api_secret)
    except Exception as exc:  # kiteconnect raises varied errors
        # Failed login exchange must not wipe an existing access_token.
        raise KiteAuthError("Token exchange failed") from exc
    access_token = data["access_token"]
    app_settings.set_setting(session, app_settings.TOKEN_KEY, access_token)
    app_settings.set_setting(
        session, app_settings.TOKEN_UPDATED_KEY, datetime.now(timezone.utc).isoformat()
    )
    return {"connected": True}


def get_access_token(session: Session) -> str | None:
    return app_settings.get_setting(session, app_settings.TOKEN_KEY)


def is_token_valid(session: Session) -> bool:
    return bool(get_access_token(session))


def clear_token(session: Session) -> None:
    for key in (app_settings.TOKEN_KEY, app_settings.TOKEN_UPDATED_KEY):
        row = session.get(Setting, key)
        if row is not None:
            session.delete(row)


def invalidate_on_kite_error(session: Session, exc: Exception) -> bool:
    """Clear stored credentials when Kite reports an authentication failure."""
    message = str(exc).lower()
    auth_markers = (
        "tokenexception",
        "invalid access token",
        "invalid token",
        "token is invalid",
        "token has expired",
        "token expired",
        "session has expired",
        "session expired",
        "invalid session",
        "authentication failed",
        "not authenticated",
        "unauthorized",
    )
    if not isinstance(exc, TokenException) and not any(marker in message for marker in auth_markers):
        return False
    clear_token(session)
    return True


def get_auth_status(session: Session) -> dict:
    return {
        "connected": is_token_valid(session),
        "credentials_configured": bool(get_settings().kite_api_key and get_settings().kite_api_secret),
        "last_sync_at": app_settings.get_setting(session, app_settings.LAST_SYNC_KEY),
        "last_trade_append_at": app_settings.get_setting(
            session, app_settings.LAST_APPEND_KEY
        ),
    }


def authenticated_kite(session: Session) -> KiteConnect:
    """Build a Kite client.

    Callers must call ``invalidate_on_kite_error`` and commit when a Kite API
    request fails so expired sessions require reconnection.
    """
    token = get_access_token(session)
    if not token:
        raise KiteAuthError("Not connected to Zerodha")
    kite = _build_kite()
    kite.set_access_token(token)
    return kite
