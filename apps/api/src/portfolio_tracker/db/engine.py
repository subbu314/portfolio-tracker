from collections.abc import Callable
from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine, Engine, event
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import sessionmaker, Session

from portfolio_tracker.config import get_settings
from portfolio_tracker.db.models import Base


def _sqlite_file_path(database_url: str) -> Path | None:
    if not database_url.startswith("sqlite"):
        return None
    url = make_url(database_url)
    if not url.database or url.database == ":memory:":
        return None
    return Path(url.database)


def _ensure_sqlite_directory(database_url: str) -> None:
    db_path = _sqlite_file_path(database_url)
    if db_path is not None:
        db_path.parent.mkdir(parents=True, exist_ok=True)


def _enable_sqlite_foreign_keys(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@lru_cache
def get_engine() -> Engine:
    url = get_settings().database_url
    _ensure_sqlite_directory(url)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args)
    if url.startswith("sqlite"):
        _enable_sqlite_foreign_keys(engine)
    return engine


@lru_cache
def get_session_factory() -> Callable[[], Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())


def reset_db_cache() -> None:
    get_engine.cache_clear()
    get_session_factory.cache_clear()
