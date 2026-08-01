from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_repo_root() -> Path:
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "apps").is_dir() and (current / "package.json").is_file():
            return current
        current = current.parent
    raise RuntimeError("Could not find repo root")


REPO_ROOT = _find_repo_root()
_DEFAULT_DATABASE_URL = f"sqlite:///{(REPO_ROOT / 'data' / 'portfolio.db').resolve().as_posix()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    kite_api_key: str = ""
    kite_api_secret: str = ""
    kite_redirect_url: str = "http://127.0.0.1:8000/auth/callback"
    database_url: str = _DEFAULT_DATABASE_URL
    cors_origins: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
