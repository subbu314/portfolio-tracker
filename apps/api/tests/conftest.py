import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _test_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("KITE_API_KEY", "test_key")
    monkeypatch.setenv("KITE_API_SECRET", "test_secret")
    monkeypatch.setenv("KITE_REDIRECT_URL", "http://127.0.0.1:8000/auth/callback")
    from portfolio_tracker.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
