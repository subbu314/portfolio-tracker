from collections.abc import Iterator

from sqlalchemy.orm import Session

from portfolio_tracker.db.engine import get_session_factory


def get_db() -> Iterator[Session]:
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
