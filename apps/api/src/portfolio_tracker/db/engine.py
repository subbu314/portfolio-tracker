from collections.abc import Callable
from functools import lru_cache

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session

from portfolio_tracker.config import get_settings
from portfolio_tracker.db.models import Base


@lru_cache
def get_engine() -> Engine:
    url = get_settings().database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


@lru_cache
def get_session_factory() -> Callable[[], Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())


def reset_db_cache() -> None:
    get_engine.cache_clear()
    get_session_factory.cache_clear()
