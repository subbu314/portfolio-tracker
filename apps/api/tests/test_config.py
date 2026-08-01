import os
from pathlib import Path

import pytest

from portfolio_tracker.config import REPO_ROOT, get_settings


def test_default_database_url_points_to_repo_root_db(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()

    api_dir = REPO_ROOT / "apps" / "api"
    original_cwd = Path.cwd()
    os.chdir(api_dir)
    try:
        settings = get_settings()
    finally:
        os.chdir(original_cwd)
        get_settings.cache_clear()

    expected_db = (REPO_ROOT / "data" / "portfolio.db").resolve()
    assert settings.database_url == f"sqlite:///{expected_db.as_posix()}"
