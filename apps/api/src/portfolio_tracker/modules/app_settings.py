from sqlalchemy.orm import Session

from portfolio_tracker.db.models import Setting

TOKEN_KEY = "kite_access_token"
TOKEN_UPDATED_KEY = "kite_token_updated_at"
LAST_SYNC_KEY = "last_sync_at"
LAST_APPEND_KEY = "last_trade_append_at"


def get_setting(session: Session, key: str) -> str | None:
    row = session.get(Setting, key)
    return row.value if row else None


def set_setting(session: Session, key: str, value: str) -> None:
    row = session.get(Setting, key)
    if row is None:
        session.add(Setting(key=key, value=value))
    else:
        row.value = value
