from pathlib import Path

import pytest

from portfolio_tracker.config import REPO_ROOT, Settings


def test_default_cors_origins_allow_both_localhost_forms(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    settings = Settings(_env_file=None)

    assert settings.cors_origins == (
        "http://localhost:3000,http://127.0.0.1:3000"
    )


def test_default_database_url_points_to_repo_root_db(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    settings = Settings(_env_file=None)

    expected_db = (REPO_ROOT / "data" / "portfolio.db").resolve()
    assert settings.database_url == f"sqlite:///{expected_db.as_posix()}"


def test_settings_loads_database_url_from_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    env_file = tmp_path / ".env"
    marker_url = "sqlite:///marker-from-env-file.db"
    env_file.write_text(f"DATABASE_URL={marker_url}\n")

    settings = Settings(_env_file=str(env_file))

    assert settings.database_url == marker_url
